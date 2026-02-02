# Migration Validation & Risk Audit

**Client:** SchemaOnly_Test_Client

**Migration:** SchemaOnly_Migration

**Audit Date:** 2026-02-02

**Auditor:** Independent Migration Audit


## Executive Summary

**Final Verdict:** NO-GO

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

- Sum Check: orders - id
- Average Check: orders - id
- Max Check: orders - id
- Min Check: orders - id
- Variance Check: orders - id
- Sum Check: orders - amount
- Average Check: orders - amount
- Max Check: orders - amount
- Min Check: orders - amount
- Variance Check: orders - amount
- Sum Check: users - id
- Average Check: users - id
- Max Check: users - id
- Min Check: users - id
- Variance Check: users - id

### Findings

- **[PASS]** Sum matches exactly for column 'id' in table 'orders'. Source and Target both have sum 210.
  - Details: {'pct_difference': np.float64(0.0)}
- **[PASS]** Average matches exactly for column 'id' in table 'orders'. Source and Target both have average 10.5.
  - Details: {'pct_difference': np.float64(0.0)}
- **[PASS]** Max matches exactly for column 'id' in table 'orders'. Source and Target both have max 20.
  - Details: {'pct_difference': np.float64(0.0)}
- **[PASS]** Min matches exactly for column 'id' in table 'orders'. Source and Target both have min 1.
  - Details: {'pct_difference': np.float64(0.0)}
- **[PASS]** Variance matches exactly for column 'id' in table 'orders'. Source and Target both have variance 35.0.
  - Details: {'pct_difference': np.float64(0.0)}
- **[PASS]** Sum matches exactly for column 'amount' in table 'orders'. Source and Target both have sum 6074.879999999999.
  - Details: {'pct_difference': np.float64(0.0)}
- **[PASS]** Average matches exactly for column 'amount' in table 'orders'. Source and Target both have average 303.74399999999997.
  - Details: {'pct_difference': np.float64(0.0)}
- **[PASS]** Max matches exactly for column 'amount' in table 'orders'. Source and Target both have max 487.05.
  - Details: {'pct_difference': np.float64(0.0)}
- **[PASS]** Min matches exactly for column 'amount' in table 'orders'. Source and Target both have min 22.94.
  - Details: {'pct_difference': np.float64(0.0)}
- **[PASS]** Variance matches exactly for column 'amount' in table 'orders'. Source and Target both have variance 15862.509698947368.
  - Details: {'pct_difference': np.float64(0.0)}
- **[PASS]** Sum matches exactly for column 'id' in table 'users'. Source and Target both have sum 210.
  - Details: {'pct_difference': np.float64(0.0)}
- **[PASS]** Average matches exactly for column 'id' in table 'users'. Source and Target both have average 10.5.
  - Details: {'pct_difference': np.float64(0.0)}
- **[PASS]** Max matches exactly for column 'id' in table 'users'. Source and Target both have max 20.
  - Details: {'pct_difference': np.float64(0.0)}
- **[PASS]** Min matches exactly for column 'id' in table 'users'. Source and Target both have min 1.
  - Details: {'pct_difference': np.float64(0.0)}
- **[PASS]** Variance matches exactly for column 'id' in table 'users'. Source and Target both have variance 35.0.
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

NO-GO
