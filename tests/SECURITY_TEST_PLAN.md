# Security Test Plan — April Ludgate (T011)

## Scope

Testing the authentication and authorization layer in `core/auth/service.py`
against OWASP Top 10 and application-specific security requirements.

## Test Categories

### 1. Authentication

| Test                      | Description                          | Status |
| ------------------------- | ------------------------------------ | ------ |
| Valid login               | Correct credentials return user      | ✅     |
| Wrong password            | Rejected with `None`                 | ✅     |
| Nonexistent user          | Rejected with `None`                 | ✅     |
| SQL injection in username | `' OR 1=1 --` rejected               | ✅     |
| Inactive user             | Deactivated user cannot authenticate | ✅     |

### 2. Password Security

| Test                       | Description                      | Status |
| -------------------------- | -------------------------------- | ------ |
| Salt uniqueness            | Same password → different hashes | ✅     |
| Empty password             | Handled without crash            | ✅     |
| Long password (1000 chars) | Handled correctly                | ✅     |
| Unicode password           | International chars + emoji work | ✅     |

### 3. RBAC Enforcement

| Action        | Admin | Auditor | Viewer |
| ------------- | ----- | ------- | ------ |
| `run_audit`   | ✅    | ✅      | ❌     |
| `view_report` | ✅    | ✅      | ✅     |
| `delete_user` | ✅    | ❌      | ❌     |

### 4. License & Access

| Test                | Description       | Status |
| ------------------- | ----------------- | ------ |
| Expired license     | Blocks all access | ✅     |
| Inactive license    | Blocks all access | ✅     |
| Inactive subscriber | Blocks all access | ✅     |
| Inactive user       | Blocks all access | ✅     |

## Future: OWASP Alignment

- [ ] Session fixation testing (after SSO implementation)
- [ ] CSRF token validation (after form implementation)
- [ ] Rate limiting (after middleware implementation)
- [ ] JWT token expiry and refresh (after OIDC implementation)
