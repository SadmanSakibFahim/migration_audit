# Test Data 2 - Complex Mapping Examples

This folder contains sample data demonstrating complex table mappings (N:1, 1:N, N:M) for the migration audit tool.

## Structure

```
test_data_2/
├── source/          # Source data files
├── target/          # Target data files
├── audit.yaml       # Configuration for complex mappings
└── README.md        # This file
```

## Examples Included

### 1. N:1 Mapping - Orders Consolidation
**Scenario:** Multiple year-based order tables merge into one consolidated table.

- **Sources:**
  - `orders_2023.csv` (5 rows)
  - `orders_2024.csv` (5 rows)
- **Target:**
  - `orders_consolidated.csv` (10 rows)
- **Mapping Type:** N:1
- **Strategy:** merge

### 2. 1:N Mapping - Customer Split
**Scenario:** One customer table splits into active and inactive customer tables.

- **Source:**
  - `customers.csv` (6 rows)
- **Targets:**
  - `customers_active.csv` (4 rows)
  - `customers_inactive.csv` (2 rows)
- **Mapping Type:** 1:N
- **Strategy:** filter

### 3. N:1 Mapping - Products Unification
**Scenario:** Multiple category-based product tables merge into one unified table.

- **Sources:**
  - `products_electronics.csv` (3 rows)
  - `products_clothing.csv` (3 rows)
- **Target:**
  - `products_unified.csv` (6 rows)
- **Mapping Type:** N:1
- **Strategy:** merge

## Running the Audit

To run the audit with this test data:

```bash
python run_audit.py --config test_data_2/audit.yaml
```

Or using the CLI:

```bash
python cli.py run --config test_data_2/audit.yaml --out reports/test_data_2_report.md
```

## Expected Results

- **Volume Checks:** Should validate that row counts match expectations for each mapping type
- **Aggregate Checks:** Should validate that sums/averages match across merged/split tables
- **Mapping Checks:** Should validate enum values in target tables
- **Data Constraint Checks:** Should validate NOT NULL and DATE constraints

## Notes

- For N:1 mappings, the target row count should equal the sum of source row counts
- For 1:N mappings, the sum of target row counts should equal the source row count
- Column mappings can be specified in the config if source and target column names differ
