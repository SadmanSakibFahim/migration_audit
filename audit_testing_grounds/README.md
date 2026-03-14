# 🧪 Audit Testing Grounds

This directory contains a suite of automated test scenarios for the Migration Audit tool. It allows you to simulate various migration outcomes—from perfect matches to catastrophic data loss or schema mismatches—and verify that the auditor behaves correctly.

## 🚀 How to Run Tests

### Run All Scenarios
To execute the entire suite of 21+ scenarios:
```bash
python audit_testing_grounds/runner.py
```
This will generate temporary data for each scenario, run the audit, and produce a markdown report in `audit_testing_grounds/[TIMESTAMP]_test_results.md`.

### Run a Specific Scenario
To run just one scenario (e.g., to debug a specific failure):
```bash
python audit_testing_grounds/runner.py --scenario [SCENARIO_NAME]
```
*Example:* `python audit_testing_grounds/runner.py --scenario type_mismatch`

### List All Scenarios
To see all available test cases:
```bash
python audit_testing_grounds/runner.py --list
```

---

## 📂 Structure

- **`data_generator/`**: Contains the logic for creating synthetic test data.
  - `generators.py`: Lower-level functions for creating DataFrames and injecting errors.
  - `scenarios.py`: The "Source of Truth" for test cases. Defines what data is generated and what the **Expected Verdict** is.
- **`runner.py`**: The main entry point for the testing suite.
- **`temp_data/`**: (Generated) Temporary CSV and DB files created during test execution.

---

## 🛠️ Key Test Categories

| Category | Description |
|----------|-------------|
| **Standard** | 1:1 migrations, volume loss, numeric mismatches, null handling. |
| **Complex** | N:1 Merges, 1:N Splits, Vertical Splits (Normalization), and N:M Re-sharding. |
| **Scalability** | Performance tests with 50k-200k rows using chunked (Incremental) processing. |
| **Chaos/Edge Cases** | Missing files, empty sources, schema mismatches, and data type corruption (Junk Detection). |
| **Features** | Mapping constraints, Relationship/FK checks, and Database-to-CSV audits. |

---

## 📝 Troubleshooting

- **Logs**: Detailed execution logs for each test run are written to `logs/audit.log`.
- **Reports**: Check the generated markdown files in this directory for a summary of passes/failures.
- **Strict Schema**: Note that the auditor is configured with **Strict Schema Validation**. If a target table is missing ANY column present in the source, it will result in an immediate `NO-GO` verdict.
