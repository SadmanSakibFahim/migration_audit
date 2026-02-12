# Compliance Test Plan — Anne Perkins (T012)

## Scope

Functional testing of compliance-related features against SOC 2 Trust Service
Criteria, focusing on PII masking, data sanitization, and security controls.

## Test Matrix

### PII Masking (DataSanitizer)

| PII Column       | Action       | Verified |
| ---------------- | ------------ | -------- |
| `email`          | SHA-256 hash | ✅       |
| `username`       | SHA-256 hash | ✅       |
| `user_id`        | SHA-256 hash | ✅       |
| `customer_email` | SHA-256 hash | ✅       |
| `patient_id`     | SHA-256 hash | ✅       |

### Sensitive Column Redaction

| Column                  | Action        | Verified |
| ----------------------- | ------------- | -------- |
| `ssn`                   | Drop entirely | ✅       |
| `credit_card`           | Drop entirely | ✅       |
| `password`              | Drop entirely | ✅       |
| `medical_record_number` | Drop entirely | ✅       |

### Edge Cases

| Scenario             | Expected            | Verified |
| -------------------- | ------------------- | -------- |
| None input           | Returns None        | ✅       |
| Empty DataFrame      | Returns empty       | ✅       |
| No PII columns       | Unchanged           | ✅       |
| Numeric PII values   | Cast to str, hashed | ✅       |
| Original not mutated | Copy-on-write       | ✅       |
| Row count preserved  | Same len()          | ✅       |

## Future Testing (Post-Implementation)

- [ ] Audit trail immutability: hash chain verification
- [ ] Data retention: automatic cleanup per tier policy
- [ ] PII auto-detection: regex + NER for unlabeled columns
- [ ] Report sanitization: CSV download endpoint applies masking
