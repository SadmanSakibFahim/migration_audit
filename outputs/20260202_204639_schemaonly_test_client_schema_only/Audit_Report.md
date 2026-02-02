# Migration Validation & Risk Audit

**Client:** SchemaOnly_Test_Client

**Migration:** SchemaOnly_Migration

**Audit Date:** 2026-02-02

**Auditor:** Independent Migration Audit


## Executive Summary

**Final Verdict:** GO

- **Data Volume Checks:** PASS
- **Aggregate Checks:** PASS
- **Data Constraint Checks:** PASS

## Data Volume Checks

### Checks Performed

- Volume Check: orders
- Volume Check: users

### Findings

- **[PASS]** Row counts match exactly for table 'orders'. Source: 20, Target: 20 rows.
- **[PASS]** Row counts match exactly for table 'users'. Source: 20, Target: 20 rows.

**Section Verdict:** PASS


## Aggregate Checks

### Checks Performed

- Sum Check: orders - amount
- Average Check: orders - amount
- Max Check: orders - amount
- Min Check: orders - amount
- Variance Check: orders - amount

### Findings

- **[PASS]** Sum matches exactly for column 'amount' in table 'orders'. Source and Target both have sum 4327.11.
  - Details: {'pct_difference': np.float64(0.0)}
- **[PASS]** Average matches exactly for column 'amount' in table 'orders'. Source and Target both have average 216.35549999999998.
  - Details: {'pct_difference': np.float64(0.0)}
- **[PASS]** Max matches exactly for column 'amount' in table 'orders'. Source and Target both have max 469.48.
  - Details: {'pct_difference': np.float64(0.0)}
- **[PASS]** Min matches exactly for column 'amount' in table 'orders'. Source and Target both have min 27.47.
  - Details: {'pct_difference': np.float64(0.0)}
- **[PASS]** Variance matches exactly for column 'amount' in table 'orders'. Source and Target both have variance 19706.754710263154.
  - Details: {'pct_difference': np.float64(0.0)}

**Section Verdict:** PASS


## Data Constraint Checks

### Checks Performed

- Data Constraints Check: orders.amount
- Data Constraints Check: orders.id
- Data Constraints Check: orders.status
- Data Constraints Check: orders.user_id
- Data Constraints Check: users.created_at
- Data Constraints Check: users.email
- Data Constraints Check: users.id
- Data Constraints Check: users.username

### Findings

- **[PASS]** All data constraints are satisfied for table 'orders'.
- **[PASS]** All data constraints are satisfied for table 'orders'.
- **[PASS]** All data constraints are satisfied for table 'orders'.
- **[PASS]** All data constraints are satisfied for table 'orders'.
- **[PASS]** All data constraints are satisfied for table 'users'.
- **[PASS]** All data constraints are satisfied for table 'users'.
- **[PASS]** All data constraints are satisfied for table 'users'.
- **[PASS]** All data constraints are satisfied for table 'users'.

**Section Verdict:** PASS


## Final Deployability Verdict

GO
