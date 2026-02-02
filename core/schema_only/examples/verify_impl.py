import sys
import os

# Ensure root is in path
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
if root_dir not in sys.path:
    sys.path.append(root_dir)

from core.schema_only.scenario_runner import ScenarioRunner

def run_test():
    runner = ScenarioRunner(temp_dir="audit_testing_grounds/verification_temp")
    
    schema_path = os.path.join(current_dir, "simple_schema.sql")
    
    scenario = {
        "schema_path": schema_path,
        "row_count": 50,
        "mutations": [
            {
                "type": "delete_row",
                "table": "users",
                "count": 10
            },
            {
                "type": "modify_value",
                "table": "orders",
                "column": "amount",
                "value": "invalid_amount"
            }
        ],
        "expected_failures": [
             {"check_name_contains": "Volume", "count": 1},
             {"check_name_contains": "Data Quality", "count": 1} 
        ]
    }
    
    print("Starting verification test...")
    result = runner.run_scenario(scenario)
    
    if result["passed"]:
        print("\n[PASS] Verification PASSED")
    else:
        print("\n[FAIL] Verification FAILED")

if __name__ == "__main__":
    run_test()
