import os
import sys

# Set up project root sys.path BEFORE any local imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

import argparse
import shutil
from datetime import datetime

import yaml
from data_generator.scenarios import SCENARIOS

from core.audit.verdict import final_verdict
from run_audit import run_audit


def setup_test_env(scenario_name: str) -> str:
    """Creates a temporary folder and generates data for the scenario."""
    base_dir = os.path.join(os.path.dirname(__file__), "temp_data", scenario_name)
    if os.path.exists(base_dir):
        shutil.rmtree(base_dir)
    os.makedirs(base_dir, exist_ok=True)

    # Generate Data
    print(f"Generating data for scenario: {scenario_name}...")
    scenario = SCENARIOS[scenario_name]
    scenario.generator_func(base_dir)

    # Generate Config
    if scenario.custom_config:
        import copy

        custom = copy.deepcopy(scenario.custom_config)

        # Check if custom_config is a single table or multiple tables
        # TableConfig has mandatory primary_key; if it's top-level, it's a single table config.
        is_single_table = any(
            k in custom for k in ["source", "target", "complex_mapping", "primary_key"]
        )
        tables = {"users": custom} if is_single_table else custom

        # Recursive path resolution
        def resolve_paths(obj):
            db_prefixes = [
                "sqlite://",
                "postgresql://",
                "mysql://",
                "mssql://",
                "oracle://",
            ]
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if k in ["path", "source", "target"] and isinstance(v, str):
                        # Don't resolve if it's already absolute or a DB URI
                        is_uri = any(v.startswith(p) for p in db_prefixes)
                        if not os.path.isabs(v) and not is_uri:
                            obj[k] = os.path.join(base_dir, v)
                        elif is_uri:
                            # For DB URIs, we need to resolve the internal file path if it's SQLite
                            if v.startswith("sqlite:///"):
                                # Format: sqlite:///relative/path/to/db/table
                                # We want to make it: sqlite:///C:/absolute/path/to/db/table
                                prefix = "sqlite:///"
                                internal_path = v[len(prefix) :]
                                if not os.path.isabs(
                                    internal_path.split("/")[0]
                                ):  # Not absolute Window path
                                    # Resolve the file part
                                    parts = internal_path.rsplit("/", 1)
                                    file_part = parts[0]
                                    table_part = parts[1] if len(parts) > 1 else ""
                                    abs_file_path = os.path.abspath(
                                        os.path.join(base_dir, file_part)
                                    )
                                    # SQLAlchemy on Windows prefers / even for paths
                                    abs_file_path = abs_file_path.replace("\\", "/")
                                    obj[k] = f"{prefix}{abs_file_path}/{table_part}"
                    else:
                        resolve_paths(v)
            elif isinstance(obj, list):
                for item in obj:
                    resolve_paths(item)

        chunk_size = custom.pop("chunk_size", None)
        resolve_paths(tables)

        config = {
            "client": "Test Client",
            "migration": {"source": "Gen Src", "target": "Gen Tgt"},
            "tolerances": {"volume_loss_pct": 1.0, "aggregate_pct_diff": 1.0},
            "chunk_size": chunk_size,
            "tables": tables,
        }
    else:
        config = {
            "client": "Test Client",
            "migration": {"source": "Generated Source", "target": "Generated Target"},
            "tolerances": {"volume_loss_pct": 1.0, "aggregate_pct_diff": 1.0},
            "tables": {
                "users": {
                    "source": os.path.join(base_dir, "source", "users.csv"),
                    "target": os.path.join(base_dir, "target", "users.csv"),
                    "primary_key": "id",
                    "aggregates": ["amount"],
                }
            },
        }

    config_path = os.path.join(base_dir, "audit.yaml")
    with open(config_path, "w") as f:
        yaml.dump(config, f)

    return config_path


def run_scenario(scenario_name: str) -> bool:
    scenario = SCENARIOS[scenario_name]
    config_path = setup_test_env(scenario_name)

    print(f"Running audit for coverage: {scenario_name}")
    try:
        results = run_audit(config_path=config_path, no_auth=True)
        print(f"DEBUG: Results for {scenario_name}:")
        for r in results:
            print(f"  - {r.name}: {r.status} (Details: {r.message})")
        verdict = final_verdict(results)

        expected = scenario.expected_result.get("verdict")

        if verdict == expected:
            print(f"[PASS]: Got {verdict} as expected.")
            return True
        else:
            print(f"[FAIL]: Expected {expected}, got {verdict}")
            return False

    except Exception as e:
        print(f"[CRASHED]: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(description="Run Testing Grounds Scenarios")
    parser.add_argument(
        "--scenario", choices=list(SCENARIOS.keys()) + ["all"], default="all"
    )
    args = parser.parse_args()

    to_run = [args.scenario] if args.scenario != "all" else SCENARIOS.keys()

    results = {}
    results_data = []  # Capture data for report

    for name in to_run:
        config_path = setup_test_env(name)
        scenario = SCENARIOS[name]

        print(f"Running audit for coverage: {name}")
        try:
            audit_results = run_audit(config_path=config_path, no_auth=True)
            verdict = final_verdict(audit_results)
            expected = scenario.expected_result.get("verdict")
            passed = verdict == expected

            results[name] = passed
            results_data.append(
                {
                    "name": scenario.name,
                    "status": passed,
                    "expected": expected,
                    "actual": verdict,
                    "description": scenario.description,
                }
            )

            if passed:
                print(f"[PASS]: Got {verdict} as expected.")
            else:
                print(f"[FAIL]: Expected {expected}, got {verdict}")
        except Exception as e:
            print(f"[CRASHED]: {e}")
            results[name] = False
            results_data.append(
                {
                    "name": scenario.name,
                    "status": False,
                    "expected": scenario.expected_result.get("verdict"),
                    "actual": "CRASHED",
                    "description": scenario.description,
                }
            )
        print("-" * 50)

    print("\nSUMMARY:")
    for name, passed in results.items():
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{name}: {status}")

    all_passed = all(results.values())

    # Generate MD Report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_filename = f"{timestamp}_test_results.md"
    report_dir = os.path.join(PROJECT_ROOT, "test_outputs", "testing_grounds")
    os.makedirs(report_dir, exist_ok=True)
    report_path = os.path.join(report_dir, report_filename)

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Testing Grounds Results\n\n")
        f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("**Suite:** Automated Run\n\n")
        f.write("## Summary\n\n")
        f.write("| Scenario | Test Result | Expected | Actual | Description |\n")
        f.write("|----------|-------------|----------|--------|-------------|\n")
        for res in results_data:
            status_icon = "✅ PASS" if res["status"] else "❌ FAIL"
            f.write(
                f"| **{res['name']}** | {status_icon} | `{res['expected']}` | `{res['actual']}` | {res['description']} |\n"
            )

    print(f"\nReport generated: {report_path}")

    if not all_passed:
        sys.exit(1)


if __name__ == "__main__":
    main()
