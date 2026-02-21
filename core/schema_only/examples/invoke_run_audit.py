import os
import sys

import yaml

# Ensure root is in path
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
if root_dir not in sys.path:
    sys.path.append(root_dir)

from core.audit.verdict import final_verdict
from core.schema_only.data_generator import DataGenerator
from core.schema_only.schema_converter import SchemaConverter
from reports.report_builder import build_report
from run_audit import run_audit


def main():
    # Setup paths
    temp_dir = os.path.join(root_dir, "audit_testing_grounds", "temp_run_audit")
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)

    schema_path = os.path.join(current_dir, "simple_schema.sql")
    config_path = os.path.join(temp_dir, "audit.yaml")

    print(f"1. Converting schema {schema_path}...")
    converter = SchemaConverter()
    config_dict = converter.convert_to_config(schema_path, format="sql")

    # Update paths in config to be absolute or relative to where we run?
    # run_audit loads config. If config has relative paths, they are relative to CWD.
    # We will run from root_dir. So paths should be relative to root or absolute.
    # Let's use absolute paths for safety.

    print(f"2. Generating data in {temp_dir}...")
    generator = DataGenerator()

    # We need to tweak the config dict to point to our temp_dir BEFORE generating data
    # explicitly, or accept what generator does and update config.
    # The generator uses the config to decide filenames?
    # No, generator.generate_data_for_config(config, output_dir)
    # writes to output_dir/{table}_source.csv

    # Generate data
    generator.generate_data_for_config(config_dict, temp_dir, row_count=20)

    # Now update config_dict to point to these generated files
    for table_name, table_config in config_dict["tables"].items():
        table_config["source"] = os.path.join(temp_dir, f"{table_name}_source.csv")
        table_config["target"] = os.path.join(
            temp_dir, f"{table_name}_target.csv"
        )  # Identical copy for now

    # Write config file
    with open(config_path, "w") as f:
        yaml.dump(config_dict, f)
    print(f"   Config written to {config_path}")

    # 3. Invoke run_audit
    print("\n3. Invoking run_audit...")
    # we must ensure os.getcwd() is root_dir for imports to work if run_audit relies on it,
    # but we already handled sys.path.

    results = run_audit(
        config_path=config_path, no_auth=True  # Bypass authentication for automated run
    )

    print(f"\nAudit completed. Total results: {len(results)}")

    # Verify Data Constraint Names
    print("\n[VERIFICATION] Data Constraint Check Names:")
    for r in results:
        if "Data Constraints" in r.name:
            print(f"  - {r.name}")

    # 4. Generate Reports
    print("\n4. Generating Reports...")
    report_paths = build_report(
        results=results,
        client="SchemaOnly_Test_Client",
        migration="SchemaOnly_Migration",
        base_dir=os.path.join(root_dir, "outputs"),
        label="_schema_only",
    )

    for fmt, path in report_paths.items():
        print(f"   - {fmt}: {path}")

    verdict = final_verdict(results)
    print(f"\nFinal Verdict: {verdict}")

    # Verify we got results
    if len(results) > 0:
        print("\nSUCCESS: run_audit executed and reports generated.")
    else:
        print("\nFAILURE: run_audit returned no results.")


if __name__ == "__main__":
    main()
