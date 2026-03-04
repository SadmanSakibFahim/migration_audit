import os
import random
import shutil
import sys
from typing import Any, Dict, List

import pandas as pd

# Ensure root is in path
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
if root_dir not in sys.path:
    sys.path.append(root_dir)

from core.audit.check_runner import CheckRunner
from core.audit.config_models import TableConfig
from core.schema_only.data_generator import DataGenerator
from core.schema_only.schema_converter import SchemaConverter


class ScenarioRunner:
    def __init__(self, temp_dir: str = "audit_testing_grounds/temp_scenario"):
        self.converter = SchemaConverter()
        self.generator = DataGenerator()
        self.temp_dir = temp_dir

    def run_scenario(self, scenario_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Runs a full scenario: schema -> data -> mutation -> audit -> verify result.
        """
        schema_path = scenario_config.get("schema_path")
        if not schema_path:
            return {"passed": False, "results": [], "audit_config": {}}
            
        schema_path_str = str(schema_path)
        if not os.path.isabs(schema_path_str):
            # Assume relative to generic data dir or provided root
            if os.path.exists(schema_path_str):
                pass
            else:
                # search or fail
                pass

        # 1. Convert Schema
        print(f"Converting schema: {schema_path_str}")
        # Detect format from extension
        ext = os.path.splitext(schema_path_str)[1].replace(".", "")
        # Fallback if unknown
        fmt = "sql" if ext == "sql" else "json"

        audit_config_dict = self.converter.convert_to_config(schema_path_str, format=fmt)

        # 2. Generate Data
        print(f"Generating data in {self.temp_dir}")
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        os.makedirs(self.temp_dir)

        self.generator.generate_data_for_config(
            audit_config_dict,
            self.temp_dir,
            row_count=scenario_config.get("row_count", 20),
        )

        # 3. Apply Mutations (Inject Faults)
        mutations = scenario_config.get("mutations", [])
        for mutation in mutations:
            self._apply_mutation(mutation)

        # 4. Run Audit
        print("Running Audit...")
        results = self._run_audit(audit_config_dict)

        # 5. Check Expectations
        expected_failures = scenario_config.get("expected_failures", [])
        pass_check = self._verify_results(results, expected_failures)

        return {
            "passed": pass_check,
            "results": results,
            "audit_config": audit_config_dict,
        }

    def _apply_mutation(self, mutation: Dict[str, Any]) -> None:
        table = mutation.get("table")
        m_type = mutation.get("type")
        target_file = os.path.join(self.temp_dir, f"{table}_target.csv")

        df = pd.read_csv(target_file)

        if m_type == "delete_row":
            count = mutation.get("count", 1)
            if len(df) > 0:
                indices_to_drop = random.sample(range(len(df)), min(count, len(df)))
                df = df.drop(indices_to_drop)
                print(
                    f"Applied mutation: Deleted {len(indices_to_drop)} rows from {table}"
                )

        elif m_type == "modify_value":
            col = mutation.get("column")
            val = mutation.get("value")
            if len(df) > 0 and col in df.columns:
                idx = random.choice(df.index)
                old_val = df.at[idx, col]
                df.at[idx, col] = val
                print(
                    f"Applied mutation: Modified {table}.{col} from {old_val} to {val} at index {idx}"
                )

        elif m_type == "nullify_value":
            col = mutation.get("column")
            if len(df) > 0 and col in df.columns:
                idx = random.choice(df.index)
                df.at[idx, col] = None
                print(f"Applied mutation: Nullified {table}.{col} at index {idx}")

        df.to_csv(target_file, index=False)

    def _run_audit(self, config_dict: Dict[str, Any]) -> List[Any]:
        all_results = []
        tables = config_dict.get("tables", {})

        for table_name, table_def in tables.items():
            # Construct TableConfig object
            # We need to ensure paths point to our temp dir
            # The generator wrote to temp_dir/{table_name}_{source|target}.csv
            # But the converter put generic paths. Overwrite them.

            src_path = os.path.join(self.temp_dir, f"{table_name}_source.csv")
            tgt_path = os.path.join(self.temp_dir, f"{table_name}_target.csv")

            # Update config dict to match where files actually are
            table_def["source"] = src_path
            table_def["target"] = tgt_path

            # Create Pydantic model
            try:
                table_config = TableConfig(**table_def)
            except Exception as e:
                print(f"Config Error for {table_name}: {e}")
                continue

            # Load DataFrames
            if not os.path.exists(src_path) or not os.path.exists(tgt_path):
                print(f"Missing files for {table_name}")
                continue

            # Naive loading, in real app we use loader.py
            src_df = pd.read_csv(src_path)
            tgt_df = pd.read_csv(tgt_path)

            runner = CheckRunner(
                table_name=table_name, meta=table_config, src_df=src_df, tgt_df=tgt_df
            )

            results = runner.execute_all()
            all_results.extend(results)

        return all_results

    def _verify_results(
        self, results: List[Any], expected_failures: List[Dict[str, Any]]
    ) -> bool:
        # Simple check: do we have failures matching expectations?
        # Expectation format: {'check_name_contains': 'Volume', 'count': 1}

        print("\n--- Audit Results ---")
        failures = []
        warnings = []

        for r in results:
            print(f"[{r.status}] {r.name}: {r.message}")
            status_str = str(r.status)
            if "FAIL" in status_str:
                failures.append(r)
            elif "WARN" in status_str:
                warnings.append(r)

        if not expected_failures and not failures:
            print("SUCCESS: No failures found, as expected.")
            return True

        if not expected_failures and failures:
            print(f"FAILURE: Found {len(failures)} unexpected failures.")
            return False

        # Check specific expectations
        all_matched = True
        for exp in expected_failures:
            pattern = exp.get("check_name_contains", "")
            exp_count = exp.get("count", 1)

            found = [f for f in failures if pattern.lower() in f.name.lower()]
            if len(found) >= exp_count:
                print(f"VERIFIED: Found expected failure matching '{pattern}'")
            else:
                print(
                    f"MISSED: Did not find expected failure matching '{pattern}' (Found {len(found)}, Expected {exp_count})"
                )
                all_matched = False

        return all_matched


if __name__ == "__main__":
    # Simple self-test
    print("ScenarioRunner Initialized")
