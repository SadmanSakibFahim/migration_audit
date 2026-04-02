# Code Review: Albatross Pro

**Project Overview**: A FastAPI-based data auditing platform with enterprise licensing, SSO, RBAC, and chunked data processing.

---

## Architecture Assessment

### Overall Structure ✅
The project is well-organized with clear separation of concerns:
- `auth/` - Authentication, licensing, and RBAC
- `core/` - Data processing runners (incremental, chunked)
- `compliance/` - Compliance checking logic
- `web/` - FastAPI app and routes

Modular design supports scalability and testability.

---

## Security Issues

### 🔴 CRITICAL: Hard-coded Fallback Secrets

**Location**: `auth/decorators.py` (line 38), `web/routes/auth.py` (line 207)

```python
secret = os.getenv("SECRET_KEY", "fallback_secret_key_used_in_tests")
```

**Problem**: Tests and development fallback keys are baked into production code. If `SECRET_KEY` env var is missing, the system silently downgrades to a known secret.

**Impact**: 
- JWT tokens can be forged with the hardcoded key
- Anyone with access to source code can impersonate any user
- Violates principle of "fail-secure"

**Fix**:
```python
secret = os.getenv("SECRET_KEY")
if not secret:
    raise ValueError("SECRET_KEY environment variable is required and must be set securely")
```

---

### 🔴 CRITICAL: Plaintext Password Logging

**Location**: `web/routes/auth.py` (lines 70-76, 82-88)

```python
log_audit_event(
    "LOGIN_FAILED",
    user_id=username,  # ← username is logged, not critical, but...
    details=f"Failed login attempt for {username}"
)
```

**Problem**: While username is logged, there's a pattern that could easily leak passwords if debugging code adds them. The `details` parameter is unvalidated.

**Fix**: Explicitly whitelist loggable fields. Never log passwords or sensitive auth material.

---

### 🟡 HIGH: Insufficient Security Headers

**Location**: `web/app.py` (lines 32-43)

```python
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        # Commented out headers:
        # response.headers["Strict-Transport-Security"] = ...
        # response.headers["Content-Security-Policy"] = ...
```

**Problem**: HSTS and CSP headers are commented out in all environments. These are fundamental for production security.

**Risks**:
- No HSTS = man-in-the-middle vulnerability on first visit
- No CSP = XSS attacks can exfiltrate data

**Fix**: Enable these headers in production. For development, use a config flag:
```python
if os.getenv("ENVIRONMENT") == "production":
    response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'; ..."
```

---

### 🟡 HIGH: Weak Password Hashing Configuration

**Location**: `auth/service.py` (line 15)

```python
def hash_password(self, password: str) -> str:
    return argon2.using(rounds=4).hash(password)  # type: ignore
```

**Problem**: Only 4 rounds of Argon2. Current best practice is 3 iterations (more iterations = slower = more secure).

**Risks**:
- Fast password cracking (4 rounds can be brute-forced on modern GPUs)
- Argon2 documentation recommends `time_cost=2, memory_cost=65536, parallelism=4` minimum

**Fix**:
```python
def hash_password(self, password: str) -> str:
    return argon2.using(time_cost=2, memory_cost=65536, parallelism=4).hash(password)
```

---

### 🟡 MEDIUM: Session Middleware Missing Secure Flags

**Location**: `web/app.py` (line 61)

```python
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
```

**Problem**: No explicit `secure=True`, `httponly=True`, `samesite="Lax"` configuration.

**Impact**: Session cookies may be transmitted over HTTP or exposed to JavaScript.

**Fix**:
```python
app.add_middleware(
    SessionMiddleware, 
    secret_key=SECRET_KEY,
    session_cookie="session",
    https_only=True,
    same_site="lax"
)
```

---

### 🟡 MEDIUM: Improper Role Serialization in SSO Flow

**Location**: `web/routes/auth.py` (line 179)

```python
"role": user.role.value if hasattr(user.role, "value") else str(user.role),
```

**Problem**: Defensive code suggests uncertainty about the role enum type. If `user.role` is sometimes a string and sometimes an enum, this is a type safety issue.

**Risk**: Role-based access control (RBAC) could be bypassed if role values are mismatched.

**Fix**: Enforce strict typing:
```python
from albatross_pro.auth.enums import UserRole

assert isinstance(user.role, UserRole), "Role must be UserRole enum"
"role": user.role.value  # Always safe
```

---

### 🟡 MEDIUM: Dangerous Path Traversal in File Upload

**Location**: `web/routes/api.py` (line 65, 77)

```python
safe_name = os.path.basename(df.filename)
dest = os.path.join("data/source", safe_name)
```

**Problem**: `os.path.basename` alone is insufficient. Filenames like `../../../etc/passwd` or null bytes can bypass it depending on OS.

**Risk**: Write arbitrary files to the filesystem.

**Fix**:
```python
import re
from pathlib import Path

# Whitelist safe characters
safe_name = re.sub(r'[^\w\-. ]', '', df.filename)
if not safe_name or safe_name.startswith('.'):
    raise ValueError("Invalid filename")

dest = Path("data/source") / safe_name
dest.resolve()  # Resolve to absolute path
if not str(dest).startswith(str(Path("data/source").resolve())):
    raise ValueError("Path traversal detected")
```

---

## Data Quality & Architecture Issues

### 🟡 HIGH: Inconsistent Abstraction in ChunkedCheckRunner

**Location**: `core/chunked_runner.py` (lines 36-64)

```python
class ChunkedCheckRunner(CheckRunner):
    def execute_chunked(self, src_iter, tgt_iter, chunk_size=10000):
        # Accumulates chunks into memory
        src_chunks = []
        tgt_chunks = []
        for i, chunk in enumerate(src_iter):
            src_chunks.append(chunk)
        
        # Then merges them
        self.src_df = pd.concat(src_chunks, ignore_index=True)
```

**Problem**: Named "chunked runner" but concatenates all chunks into memory, negating the memory benefit of streaming. This defeats the purpose of chunking.

**Impact**:
- Large datasets still cause OOM
- False expectation of memory efficiency
- Inconsistent with `IncrementalRunner` which truly streams

**Fix**: Either:
1. Make it truly incremental like `IncrementalRunner`
2. Or rename to `BatchProcessor` and document memory requirements
3. Add warnings when chunk_count × chunk_size exceeds memory threshold

---

### 🟠 MEDIUM: License Validity Check Ignores Timezones

**Location**: `auth/service.py` (lines 99-103)

```python
def is_license_valid(self, license_obj: License) -> bool:
    now = datetime.now()
    # In case dates are timezone naive...
    # Here we just compare naive against naive for MVP simplicity
    return bool(license_obj.valid_from <= now <= license_obj.valid_until)
```

**Problem**: Mixing naive and timezone-aware datetimes is a known footgun. The comment acknowledges this but accepts it as MVP limitation.

**Risk**:
- If DB stores UTC but `datetime.now()` is local, licenses expire at wrong times
- Inconsistent behavior across timezones
- Hard to debug in production

**Fix**:
```python
from datetime import datetime, timezone

def is_license_valid(self, license_obj: License) -> bool:
    # Always use UTC
    now = datetime.now(timezone.utc)
    # Ensure DB dates are also UTC-aware
    valid_from = license_obj.valid_from.replace(tzinfo=timezone.utc)
    valid_until = license_obj.valid_until.replace(tzinfo=timezone.utc)
    return valid_from <= now <= valid_until
```

---

### 🟠 MEDIUM: Weak Sampling Strategy in IncrementalRunner

**Location**: `core/incremental_runner.py` (lines 42-49)

```python
# Identity Sampling (Reservoir Sampling)
self.sample_size = 1000
self.src_pk_sample: List[Any] = []
```

**Problem**: Hard-coded sample size of 1,000. No statistical validation of whether this is sufficient.

**For a table with 1,000,000 rows**:
- 1,000 sample size = 0.1% coverage
- If 99.9% of records exist in target, sample only finds ~998
- Pass rate becomes: 998/1000 = 99.8% (line 199: threshold is 95%, so PASS)
- But actual loss could be 10,000 rows (1% of 1M)

**Fix**:
```python
# Adaptive sample size based on row count
def __init__(self, ...):
    # At minimum, sample sqrt(n) or 5,000, whichever is larger
    estimated_rows = getattr(meta, "estimated_row_count", 1_000_000)
    self.sample_size = max(int(estimated_rows ** 0.5), 5000)
    
    # Document margin of error
    # sample_size=5000 from 1M rows = 0.5% margin of error at 95% CI
```

---

### 🟠 MEDIUM: Junk Detection is Lossy

**Location**: `core/incremental_runner.py` (lines 116-121)

```python
# Junk detection: count non-numeric values that aren't NaN
vals_coerced = pd.to_numeric(chunk[col], errors="coerce")
junk_count = chunk[col].notna().sum() - vals_coerced.notna().sum()
```

**Problem**: Only counts junk; doesn't report which values are junk. "Found 1,234 junk values" doesn't help debugging.

**Fix**:
```python
# Collect actual junk values (sample up to 50)
junk_values = chunk[col][chunk[col].notna() & vals_coerced.isna()].unique()[:50]
self.junk_samples[col] = list(junk_values)

# In finalize():
details={"junk_count": count, "samples": self.junk_samples.get(col, [])},
```

---

## Code Quality Issues

### 🟠 MEDIUM: No Request ID for Tracing

**Location**: `web/app.py` (db_session_middleware)

```python
@app.middleware("http")
async def db_session_middleware(request: Request, call_next):
    request.state.db = SessionLocal()
```

**Problem**: No unique request ID. If audits fail, you can't correlate logs across services.

**Fix**:
```python
import uuid

@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request.state.request_id = str(uuid.uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    return response
```

Then use `request.state.request_id` in all logging.

---

### 🟠 MEDIUM: Silent Exception Swallowing

**Location**: `web/app.py` (lines 25-28)

```python
finally:
    try:
        request.state.db.close()
    except Exception:
        pass  # Silent fail
```

**Problem**: Silently ignores database close errors. This can hide connection pool exhaustion.

**Fix**:
```python
finally:
    try:
        request.state.db.close()
    except Exception as e:
        logger.warning(f"Failed to close DB session: {e}")
```

---

### 🟠 MEDIUM: Enum Handling Inconsistency

**Location**: Multiple files (`auth/decorators.py`, `auth/service.py`)

**Problem**: Code uses both `user.role` (enum) and `user.role.value` (string) interchangeably.

```python
# In one place:
"role": user.role.value if hasattr(user.role, "value") else str(user.role)

# In another:
payload = {"role": user.role.value if hasattr(user.role, "value") else str(user.role)}
```

**Risk**: Defensive checks suggest type uncertainty. Type hints should be strict.

**Fix**:
```python
# auth/models.py
role: UserRole = Column(SqEnum(UserRole), default=UserRole.VIEWER)

# Always use role.value
"role": user.role.value  # No type: ignore or hasattr checks needed
```

---

### 🟠 MEDIUM: Magic Numbers Without Documentation

**Location**: `core/incremental_runner.py` (line 199)

```python
status = (
    CheckStatus.PASS
    if overlap_pct >= 95
    else (CheckStatus.WARN if overlap_pct > 0 else CheckStatus.FAIL)
)
```

**Problem**: Why 95%? What statistical confidence is this?

**Fix**:
```python
# Constant at module level with justification
IDENTITY_OVERLAP_THRESHOLD = 0.95  # 95% overlap = 95% CI, sample_size=1000

status = (
    CheckStatus.PASS
    if overlap_pct >= IDENTITY_OVERLAP_THRESHOLD * 100
    ...
)
```

---

### 🟡 MEDIUM: Import Patterns Are Inconsistent

**Location**: `core/incremental_runner.py` (lines 88-89)

```python
def process_target(self, path: str) -> None:
    from checks.data_constraints import check_data_constraints
    from core.audit.check_registry import CHECK_REGISTRY
```

**Problem**: Late imports inside methods. Makes dependencies unclear and hides circular import issues.

**Fix**:
```python
# At top of file
from checks.data_constraints import check_data_constraints
from core.audit.check_registry import CHECK_REGISTRY

# Then use normally
```

**Exception**: Late imports can be OK for heavy dependencies not always needed, but document why.

---

## Testing & Observability

### 🟠 MEDIUM: No Type Hints on Core Methods

**Location**: `core/incremental_runner.py` (line 51-52)

```python
def process_source(self, path: str) -> None:
    chunks = load_table(path, chunk_size=self.chunk_size)  # What type is chunks?
```

**Problem**: `load_table` return type is unknown. Type checking can't validate iteration.

**Fix**:
```python
from typing import Iterator
import pandas as pd

def load_table(path: str, chunk_size: int) -> Iterator[pd.DataFrame]:
    """Load data in chunks. Yields DataFrames of size chunk_size."""
    ...

def process_source(self, path: str) -> None:
    chunks: Iterator[pd.DataFrame] = load_table(path, self.chunk_size)
```

---

### 🟠 MEDIUM: IncrementalRunner has Race Condition Risk

**Location**: `core/incremental_runner.py` (lines 30-31)

```python
self.is_cancelled_callback: Optional[Any] = is_cancelled_callback
```

Then used in:
```python
if self.is_cancelled_callback and self.is_cancelled_callback():
    return
```

**Problem**: `is_cancelled_callback` is checked every chunk, but if it's a shared reference to external state, race conditions are possible. Also `Any` type hides what the callback actually is.

**Fix**:
```python
from typing import Callable

self.is_cancelled_callback: Optional[Callable[[], bool]] = is_cancelled_callback

# And validate it's actually callable
if self.is_cancelled_callback is not None:
    assert callable(self.is_cancelled_callback), "Callback must be callable"
```

---

## Database Concerns

### 🟠 MEDIUM: No Connection Pool Configuration

**Location**: `web/routes/auth.py` (line 38)

```python
engine = create_engine(DB_PATH, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
```

**Problem**: No pool_size, pool_pre_ping, or max_overflow configuration. Default pool size is 5.

**Risk**:
- Under load, connection pool exhausts → 503 errors
- Stale connections from network issues are reused
- No monitoring of pool health

**Fix**:
```python
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DB_PATH,
    connect_args=connect_args,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=3600,   # Recycle connections hourly
    echo=False  # Set to True for SQL debugging
)
```

---

### 🟠 MEDIUM: No Transaction Management in Audit Routes

**Location**: `web/routes/auth.py` (lines 66-79)

```python
auth = AuthService(db)
user = auth.authenticate_user(username, password)
if not user:
    log_audit_event(...)  # What if this fails?
    return templates.TemplateResponse(...)
```

**Problem**: If `log_audit_event` raises an exception, the response is still sent. No rollback guarantee.

**Fix**:
```python
try:
    auth = AuthService(db)
    user = auth.authenticate_user(username, password)
    if not user:
        try:
            log_audit_event(...)
        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")
        return templates.TemplateResponse(...)
    db.commit()  # Only commit after successful login
except Exception:
    db.rollback()
    raise
```

---

## Recommendations Summary

| Priority | Issue | Effort | Impact |
|----------|-------|--------|--------|
| 🔴 CRITICAL | Hard-coded fallback secrets | 15min | High - JWT forgery risk |
| 🔴 CRITICAL | File upload path traversal | 30min | High - RCE potential |
| 🟡 HIGH | Missing security headers | 30min | High - MITM/XSS risk |
| 🟡 HIGH | Weak password hashing | 15min | High - Password cracking |
| 🟠 MEDIUM | Chunked runner concatenates to memory | 2hrs | Medium - OOM on large data |
| 🟠 MEDIUM | Session cookie flags | 15min | Medium - Cookie theft |
| 🟠 MEDIUM | Timezone-aware license checks | 1hr | Medium - License bypass |
| 🟠 MEDIUM | Weak sampling strategy | 2hrs | Medium - Data loss undetected |

---

## Strengths ✅

1. **Modular architecture** - Clean separation of auth, core logic, web layer
2. **Comprehensive testing** - ~20 test files suggest good coverage
3. **Audit logging** - All auth events are logged
4. **RBAC implementation** - Role-based permissions with clear hierarchy
5. **Incremental processing** - True streaming approach for large datasets
6. **Multi-auth support** - Both local + SSO integration
7. **License management** - Proper enterprise licensing structure

---

## Next Steps

1. **Immediate (This sprint)**:
   - Remove hard-coded fallback secrets
   - Fix file upload path traversal
   - Enable HSTS/CSP headers

2. **Short-term (1-2 sprints)**:
   - Upgrade password hashing config
   - Add session cookie security flags
   - Fix timezone-aware datetime handling
   - Add request IDs to all logs

3. **Medium-term (Sprint planning)**:
   - Refactor `ChunkedCheckRunner` or rename it
   - Improve sampling validation in `IncrementalRunner`
   - Add connection pool configuration
   - Add type hints throughout
   - Improve exception handling in middleware

4. **Code quality improvements**:
   - Add pre-commit hooks (black, flake8, mypy)
   - Enable stricter type checking (no `Any` without justification)
   - Document all magic numbers and thresholds
   - Add docstrings to public methods
