# Invalid Rows Filtering Feature

**Feature:** Ignore invalid rows during audit execution  
**CLI Argument:** `--ignore-invalid-rows`  
**Status:** Implemented

---

## Overview

This feature allows the audit tool to continue processing even when encountering invalid rows in source or target data files. Invalid rows are identified, logged, and exported to CSV files for review, while the audit proceeds with only valid data.

---

## Usage

### CLI Command

```bash
python cli.py run \
  --config config/audit.yaml \
  --out reports/audit_report.docx \
  --client "Your Company" \
  --migration "Source → Target" \
  --ignore-invalid-rows
```

### Programmatic Usage

```python
from run_audit import run_audit

results = run_audit(
    config_path="config/audit.yaml",
    ignore_invalid_rows=True
)
```

---

## What Makes a Row Invalid?

A row is considered invalid if it violates any of the following constraints defined in the audit configuration:

### 1. Data Constraints (NOT NULL)
- Rows with null or empty values in columns marked as `not_null` in `data_constraints`

### 2. Data Constraints (DATE)
- Rows with invalid date values in columns marked as `date` in `data_constraints`

### 3. Mapping Constraints
- Rows with values not in the `allowed_values` list for columns defined in `mappings` (target data only)

### 4. Primary Key Uniqueness
- Rows with duplicate primary key values (target data only, flags duplicates after first occurrence)

---

## Output Files

### Invalid Row CSV Files

For each file with invalid rows, a CSV file is created in the `invalid_data` subfolder:

**Location:** `{source_or_target_directory}/invalid_data/{original_filename}_invalid_{source|target}.csv`

**Example:**
- Source file: `data/source/users.csv`
- Invalid rows exported to: `data/source/invalid_data/users_invalid_source.csv`
- Target file: `data/target/users.csv`
- Invalid rows exported to: `data/target/invalid_data/users_invalid_target.csv`

**CSV Format:**
- All original columns from the source file
- Additional column: `_row_index` - Original row index in the file
- Additional column: `_validation_errors` - Semicolon-separated list of validation errors

### Summary Log File

A summary log file is created in the same directory as the configuration file:

**Location:** `{config_directory}/invalid_rows_summary_{timestamp}.log`

**Contents:**
- Total count of invalid rows
- Breakdown by table
- For each invalid row:
  - File path and type (source/target)
  - Row index
  - Validation errors
  - Export file location

---

## Example

### Configuration

```yaml
tables:
  users:
    source: data/source/users.csv
    target: data/target/users.csv
    primary_key: id
    data_constraints:
      email: [not_null]
      date_of_birth: 
        - not_null
        - date
    mappings:
      - columns: [status]
        allowed_values: [active, inactive, suspended]
```

### Sample Invalid Rows CSV

```csv
id,first_name,last_name,email,date_of_birth,status,_row_index,_validation_errors
5,John,Doe,,2020-01-15,active,4,"Column 'email' is null (not_null constraint)"
6,Jane,Smith,jane@example.com,invalid-date,active,5,"Column 'date_of_birth' has invalid date value: invalid-date"
7,Bob,Johnson,bob@example.com,1990-05-20,pending,6,"Column 'status' has invalid value 'pending' (allowed: active, inactive, suspended)"
```

### Sample Summary Log

```
================================================================================
INVALID ROWS SUMMARY LOG
================================================================================
Generated: 2026-01-25 18:30:45
Total invalid rows: 3
================================================================================

Table: users
--------------------------------------------------------------------------------
Total invalid rows: 3

  File: data/source/users.csv (source)
  Row Index: 4
  Reasons: Column 'email' is null (not_null constraint)
  Exported to: data/source/invalid_data/users_invalid_source.csv

  File: data/target/users.csv (target)
  Row Index: 5
  Reasons: Column 'date_of_birth' has invalid date value: invalid-date
  Exported to: data/target/invalid_data/users_invalid_target.csv

  File: data/target/users.csv (target)
  Row Index: 6
  Reasons: Column 'status' has invalid value 'pending' (allowed: active, inactive, suspended)
  Exported to: data/target/invalid_data/users_invalid_target.csv
```

---

## Behavior

### When `--ignore-invalid-rows` is NOT specified (default):
- Invalid rows are included in the audit
- Validation checks will fail if constraints are violated
- No CSV files are exported
- Standard audit behavior

### When `--ignore-invalid-rows` IS specified:
- Invalid rows are excluded from all checks
- Audit proceeds with only valid rows
- Invalid rows are logged and exported
- Volume checks reflect only valid rows
- Aggregate checks use only valid rows
- Relationship checks use only valid rows

---

## Complex Mappings

For complex mappings (N:1, 1:N, N:M):

- Each source file is validated individually before merging
- Each target file is validated individually before merging
- Invalid rows from each file are exported separately
- Only valid rows participate in the merge operation

**Example:**
- `orders_2023.csv` → validated → invalid rows exported → valid rows merged
- `orders_2024.csv` → validated → invalid rows exported → valid rows merged
- Both valid sets merged into final source DataFrame

---

## Logging

The feature logs:
- Number of invalid rows found per file
- Export file locations
- Summary log creation

All logging uses the standard logger with INFO level.

---

## Notes

1. **Row Index Preservation:** The `_row_index` column in exported CSVs refers to the original row index in the source file, not the filtered DataFrame.

2. **Multiple Errors:** A single row can have multiple validation errors. All errors are captured in the `_validation_errors` column.

3. **File Organization:** Invalid data files are organized in `invalid_data` subfolders to keep them separate from source/target data.

4. **Non-Destructive:** Original source and target files are never modified. Only new files are created in the `invalid_data` subfolder.

5. **Performance:** Validation adds minimal overhead. For large files, validation is performed row-by-row but efficiently.

---

## Use Cases

1. **Data Quality Assessment:** Identify data quality issues before fixing them
2. **Partial Audits:** Continue audit even when some data is problematic
3. **Data Cleanup:** Export invalid rows for manual review and correction
4. **Migration Planning:** Understand scope of data issues before migration

---

## Future Enhancements

Potential improvements:
- Configurable validation rules
- Custom validation functions
- Validation report generation
- Integration with data quality tools
- Automatic row correction suggestions

---

**Last Updated:** January 25, 2026
