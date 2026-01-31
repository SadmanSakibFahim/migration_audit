# Migration Validation & Risk Audit

**Client:** Acme Corp

**Migration:** Legacy DB -> Cloud SQL

**Audit Date:** 2026-01-31

**Auditor:** Independent Migration Audit


## Executive Summary

**Final Verdict:** NO-GO

- **Data Volume Checks:** FAIL
- **Aggregate Checks:** PASS
- **Mapping Checks:** FAIL
- **Data Constraint Checks:** PASS

## Data Volume Checks

### Checks Performed

- Volume Check: orders_consolidated
- Volume Check: customers_split
- Volume Check: products_unified

### Findings

- **[FAIL]** Row count difference exceeds tolerance for table 'orders_consolidated'. Source: 10, Target: 10, Difference: 100.00%. Expected ~5 target rows (ratio 0.50)
- **[FAIL]** Row count difference exceeds tolerance for table 'customers_split'. Source: 6, Target: 6, Difference: 50.00%. Expected ~12 target rows (ratio 2.00)
- **[FAIL]** Row count difference exceeds tolerance for table 'products_unified'. Source: 6, Target: 6, Difference: 100.00%. Expected ~3 target rows (ratio 0.50)

**Section Verdict:** FAIL


## Aggregate Checks

### Checks Performed

- Sum Check: orders_consolidated - amount
- Average Check: orders_consolidated - amount
- Max Check: orders_consolidated - amount
- Min Check: orders_consolidated - amount
- Variance Check: orders_consolidated - amount
- Sum Check: orders_consolidated - quantity
- Average Check: orders_consolidated - quantity
- Max Check: orders_consolidated - quantity
- Min Check: orders_consolidated - quantity
- Variance Check: orders_consolidated - quantity
- Sum Check: customers_split - balance
- Average Check: customers_split - balance
- Max Check: customers_split - balance
- Min Check: customers_split - balance
- Variance Check: customers_split - balance
- Sum Check: products_unified - price
- Average Check: products_unified - price
- Max Check: products_unified - price
- Min Check: products_unified - price
- Variance Check: products_unified - price
- Sum Check: products_unified - stock_quantity
- Average Check: products_unified - stock_quantity
- Max Check: products_unified - stock_quantity
- Min Check: products_unified - stock_quantity
- Variance Check: products_unified - stock_quantity

### Findings

- **[PASS]** Sum matches exactly for column 'amount' in table 'orders_consolidated'. Source and Target both have sum 1753.72.
  - Details: {'pct_difference': np.float64(0.0)}
- **[PASS]** Average matches exactly for column 'amount' in table 'orders_consolidated'. Source and Target both have average 175.372.
  - Details: {'pct_difference': np.float64(0.0)}
- **[PASS]** Max matches exactly for column 'amount' in table 'orders_consolidated'. Source and Target both have max 320.0.
  - Details: {'pct_difference': np.float64(0.0)}
- **[PASS]** Min matches exactly for column 'amount' in table 'orders_consolidated'. Source and Target both have min 89.99.
  - Details: {'pct_difference': np.float64(0.0)}
- **[PASS]** Variance matches exactly for column 'amount' in table 'orders_consolidated'. Source and Target both have variance 5084.231551111112.
  - Details: {'pct_difference': np.float64(0.0)}
- **[PASS]** Sum matches exactly for column 'quantity' in table 'orders_consolidated'. Source and Target both have sum 21.
  - Details: {'pct_difference': np.float64(0.0)}
- **[PASS]** Average matches exactly for column 'quantity' in table 'orders_consolidated'. Source and Target both have average 2.1.
  - Details: {'pct_difference': np.float64(0.0)}
- **[PASS]** Max matches exactly for column 'quantity' in table 'orders_consolidated'. Source and Target both have max 4.
  - Details: {'pct_difference': np.float64(0.0)}
- **[PASS]** Min matches exactly for column 'quantity' in table 'orders_consolidated'. Source and Target both have min 1.
  - Details: {'pct_difference': np.float64(0.0)}
- **[PASS]** Variance matches exactly for column 'quantity' in table 'orders_consolidated'. Source and Target both have variance 0.9888888888888892.
  - Details: {'pct_difference': np.float64(0.0)}
- **[PASS]** Sum matches exactly for column 'balance' in table 'customers_split'. Source and Target both have sum 9501.25.
  - Details: {'pct_difference': np.float64(0.0)}
- **[PASS]** Average matches exactly for column 'balance' in table 'customers_split'. Source and Target both have average 1583.5416666666667.
  - Details: {'pct_difference': np.float64(0.0)}
- **[PASS]** Max matches exactly for column 'balance' in table 'customers_split'. Source and Target both have max 3200.0.
  - Details: {'pct_difference': np.float64(0.0)}
- **[PASS]** Min matches exactly for column 'balance' in table 'customers_split'. Source and Target both have min 200.0.
  - Details: {'pct_difference': np.float64(0.0)}
- **[PASS]** Variance matches exactly for column 'balance' in table 'customers_split'. Source and Target both have variance 1253875.1104166668.
  - Details: {'pct_difference': np.float64(0.0)}
- **[PASS]** Sum matches exactly for column 'price' in table 'products_unified'. Source and Target both have sum 2259.9399999999996.
  - Details: {'pct_difference': np.float64(0.0)}
- **[PASS]** Average matches exactly for column 'price' in table 'products_unified'. Source and Target both have average 376.6566666666666.
  - Details: {'pct_difference': np.float64(0.0)}
- **[PASS]** Max matches exactly for column 'price' in table 'products_unified'. Source and Target both have max 999.99.
  - Details: {'pct_difference': np.float64(0.0)}
- **[PASS]** Min matches exactly for column 'price' in table 'products_unified'. Source and Target both have min 19.99.
  - Details: {'pct_difference': np.float64(0.0)}
- **[PASS]** Variance matches exactly for column 'price' in table 'products_unified'. Source and Target both have variance 161946.6666666667.
  - Details: {'pct_difference': np.float64(0.0)}
- **[PASS]** Sum matches exactly for column 'stock_quantity' in table 'products_unified'. Source and Target both have sum 655.
  - Details: {'pct_difference': np.float64(0.0)}
- **[PASS]** Average matches exactly for column 'stock_quantity' in table 'products_unified'. Source and Target both have average 109.16666666666667.
  - Details: {'pct_difference': np.float64(0.0)}
- **[PASS]** Max matches exactly for column 'stock_quantity' in table 'products_unified'. Source and Target both have max 200.
  - Details: {'pct_difference': np.float64(0.0)}
- **[PASS]** Min matches exactly for column 'stock_quantity' in table 'products_unified'. Source and Target both have min 50.
  - Details: {'pct_difference': np.float64(0.0)}
- **[PASS]** Variance matches exactly for column 'stock_quantity' in table 'products_unified'. Source and Target both have variance 3104.166666666667.
  - Details: {'pct_difference': np.float64(0.0)}

**Section Verdict:** PASS


## Mapping Checks

### Checks Performed

- Mapping Check: orders_consolidated
- Mapping Check: customers_split
- Mapping Check: products_unified

### Findings

- **[PASS]** All mappings are valid for table 'orders_consolidated'.
- **[FAIL]** Mapping issues found in table 'customers_split': Column 'status' is missing in table 'customers_split'.
  - Details: {'issues': ["Column 'status' is missing in table 'customers_split'."]}
- **[PASS]** All mappings are valid for table 'products_unified'.

**Section Verdict:** FAIL


## Data Constraint Checks

### Checks Performed

- Data Constraints Check: orders_consolidated
- Data Constraints Check: orders_consolidated
- Data Constraints Check: orders_consolidated
- Data Constraints Check: customers_split
- Data Constraints Check: customers_split
- Data Constraints Check: products_unified
- Data Constraints Check: products_unified
- Data Constraints Check: products_unified

### Findings

- **[PASS]** All data constraints are satisfied for table 'orders_consolidated'.
- **[PASS]** All data constraints are satisfied for table 'orders_consolidated'.
- **[PASS]** All data constraints are satisfied for table 'orders_consolidated'.
- **[PASS]** All data constraints are satisfied for table 'customers_split'.
- **[PASS]** All data constraints are satisfied for table 'customers_split'.
- **[PASS]** All data constraints are satisfied for table 'products_unified'.
- **[PASS]** All data constraints are satisfied for table 'products_unified'.
- **[PASS]** All data constraints are satisfied for table 'products_unified'.

**Section Verdict:** PASS


## Final Deployability Verdict

NO-GO
