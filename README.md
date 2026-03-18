# Migration Validation & Risk Audit Framework

![Web Dashboard](screenshots/web_dashboard.png)

A production-grade, configuration-driven data migration audit framework that validates correctness, integrity, and deployment readiness of data migrations across multiple dimensions.

**Version**: 0.9.0 · **Sprint**: Foundation & Polish (Feb 10–24, 2026)

**Core Question:** Is the migrated system safe to deploy?

---

## 📋 Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Installation](#installation)
- [Usage](#usage)
- [Web Dashboard](#web-dashboard)
- [Docker Deployment](#docker-deployment)
- [Validation Dimensions](#validation-dimensions)
- [Output & Verdict](#output--verdict)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [Testing](#testing)
- [Design Decisions](#design-decisions)
- [Design Principles](#design-principles)
- [Roadmap](#roadmap)

## Overview

This tool provides a standardized, reusable framework for auditing data migrations against **five critical validation dimensions**. It produces a clear **GO / GO WITH WARNINGS / NO-GO** deployment verdict based on configurable business rules and tolerance thresholds.

### Key Strengths

- **Config-driven**: All table names, columns, and tolerances defined in a single YAML file
- **Multi-source**: Load data from CSV files or databases (PostgreSQL, MySQL, SQLite, SQL Server, Oracle) via a unified DataSource abstraction
- **Web dashboard**: Dark-themed glassmorphism UI with drag-and-drop upload, live audit progress via SSE
- **Docker-ready**: Multi-stage build with health checks, non-root user, optimized image size
- **Production-grade**: Graceful error handling, null guards, type validation across all check modules
- **Business-focused**: Reports map directly to executive-readable audit conclusions

## Key Features

| Feature                    | Description                                                             |
| -------------------------- | ----------------------------------------------------------------------- |
| **Volume Integrity**       | Validates complete data migration within acceptable loss tolerance      |
| **Relationship Integrity** | Verifies foreign key constraints and prevents orphaned records          |
| **Aggregate Consistency**  | Confirms counts, sums, and statistics match source system               |
| **Mapping Validation**     | Validates enum, status, and code transformations                        |
| **Data Constraints**       | Enforces not-null, date format, and data type validations               |
| **Automated Verdicts**     | Generates deployment-ready GO/NO-GO decisions                           |
| **Web Dashboard**          | Real-time audit monitoring with file upload wizard                      |
| **Database Support**       | Connect to PostgreSQL, MySQL, SQLite, SQL Server, Oracle via SQLAlchemy |
| **PII Masking**            | SHA-256 hashing and column dropping for sensitive data                  |
| **Auth & RBAC**            | Role-based access control (Admin / Auditor / Viewer)                    |

## Open Core vs Premium

This repository is structured as an **open-core project**:

- ✅ **Open Core (this repo)**: contains the **CLI audit engine**, configuration-driven checks, reporting, and the core data validation framework.
- 🔒 **Premium (optional)**: advanced features live under `albatross_pro/`, including the **web dashboard**, **auth/RBAC**, **user management**, and **enterprise deployment helpers**.

> The core CLI audit engine can be used standalone without installing or running the premium modules.

> If `albatross_pro` is installed & configured, `run_audit.py` will attempt to authenticate users via the premium auth service. Use `--no-auth` to skip this and run in open-core mode.

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│               Web Dashboard (FastAPI + Jinja2)               │
│               Drag-and-drop Upload · Live SSE Progress       │
├──────────────────────────────────────────────────────────────┤
│                     FastAPI + Uvicorn                         │
│               REST API · Auth · Session Mgmt                 │
├──────────────────────────────────────────────────────────────┤
│                     Core Audit Engine                         │
│   CheckRunner → Volume │ Identity │ Aggregates │ Mappings    │
│                   Relationships │ Data Constraints            │
├──────────────────────────────────────────────────────────────┤
│                     DataSource Layer                          │
│            CSVDataSource  │  DatabaseDataSource (SQLAlchemy)  │
├──────────────────────────────────────────────────────────────┤
│                     Data & Config                             │
│              CSV Files · PostgreSQL · MySQL · SQLite          │
└──────────────────────────────────────────────────────────────┘
```

## Installation

### Prerequisites

- Python 3.10 or higher
- pip package manager

### Step 1: Create Virtual Environment

```bash
# On Linux / macOS
python3 -m venv venv
source venv/bin/activate

# On Windows
python -m venv venv
venv\Scripts\activate
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Verify Installation

```bash
python3 -c "import pandas; import sqlalchemy; import fastapi; print('✓ All dependencies installed')"
```

## Usage

### CLI Audit (Core Engine)

```bash
# Run audit on all configured tables (default: config/audit.yaml)
python3 run_audit.py

# Run audit on specific tables
python3 run_audit.py --tables users orders

# Run audit without authentication (no `albatross_pro` required)
python3 run_audit.py --no-auth

# Run in fully headless/CI mode (outputs JSON)
python3 run_audit.py --no-auth --headless

# Dry-run (validates configuration and data loading without running checks)
python3 run_audit.py --dry-run

# Ignore/strip invalid rows (writes invalid rows to a summary log)
python3 run_audit.py --ignore-invalid-rows

# Override config path
python3 run_audit.py --config path/to/your/audit.yaml
```

![CLI Audit Demo](screenshots/terminal_demo_snap.png)

### Generating Random Test Data

A helper script can generate randomized source/target CSVs plus a matching YAML config to exercise every check type. By default it writes to `random_data/`.

```bash
python3 scripts/generate_comprehensive_test_data.py --rows 150 --fail-rate 0.35
```

By default this script produces non-deterministic test data each run. Use `--seed <n>` to reproduce the same dataset.

You can also change the output location:

```bash
python3 scripts/generate_comprehensive_test_data.py --out-dir random_data/test_case
```

### What Happens During Audit

1. **Load Configuration** — Reads `config/audit.yaml`
2. **Validate DataFrames** — Checks for None, wrong types, empty data
3. **Execute Checks** — Runs all validation checks (with `_safe_run()` error isolation)
4. **Aggregate Results** — Collects check results by severity
5. **Compute Verdict** — Determines GO / NO-GO / GO WITH WARNINGS
6. **Generate Reports** — Produces HTML, PDF, Markdown, and JSON reports

## Web Dashboard

The web dashboard provides a 3-step wizard for running audits:

1. **Upload** — Drag-and-drop config YAML and CSV data files
2. **Select Scope** — Choose which tables to audit
3. **Monitor** — Watch live progress via Server-Sent Events (SSE)

![Audit Results Page](screenshots/results_page.png)

### Starting the Dashboard (Premium)

```bash
# Direct: run Uvicorn against the FastAPI app
uvicorn albatross_pro.web.app:app --host 0.0.0.0 --port 8000 --reload

# Shortcut: use the helper script (runs on port 8001)
python3 run_dashboard.py
```

Then open [http://localhost:8000](http://localhost:8000) (or [http://localhost:8001](http://localhost:8001) when using the helper script) in your browser.

### API Endpoints

| Method | Endpoint                     | Auth    | Description                      |
| ------ | ---------------------------- | ------- | -------------------------------- |
| POST   | `/api/upload`                | Auditor | Upload config YAML + CSV files   |
| GET    | `/api/config`                | Viewer  | Get available tables from config |
| POST   | `/api/audit/start`           | Auditor | Trigger a new audit run          |
| GET    | `/api/stream`                | Viewer  | SSE stream for live progress     |
| GET    | `/api/reports`               | Viewer  | List generated reports           |
| GET    | `/api/reports/{id}/download` | Viewer  | Download report file (sanitized) |

## Docker Deployment

### Build & Run

```bash
# Build the optimized image
docker build -t migration-audit .

# Run with docker-compose
docker compose up -d

# Verify health
curl http://localhost:8000/health
```

### Smoke Test

```bash
bash scripts/smoke_test.sh
```

The smoke test builds the image, verifies size (<400MB target), starts the container, checks endpoints, validates health, and cleans up.

### Docker Features

- **Multi-stage build** — Builder + runtime stages for minimal image size
- **Non-root user** — Runs as `appuser` (UID 1000) for security
- **Health check** — Built-in `/health` endpoint monitoring
- **Log rotation** — JSON logging with 10MB max size, 3 file rotation

## Validation Dimensions

The audit engine performs validation across **13+ check types** organized into five core dimensions:

### 1. Volume Integrity

Compares record counts between source and target. Supports 1:N and N:1 mapping types with configurable tolerance.

```yaml
tolerances:
  volume_loss_pct: 0.1 # Max 0.1% loss allowed
```

**Checks**: Row count comparison, 1:N/N:1 mapping validation, loss percentage calculation

### 2. Identity Integrity

Validates primary key overlap and detects null PKs or missing record identifiers.

```yaml
tables:
  orders:
    primary_key: id
    identity_overlap_threshold: 95  # Min % of PKs that must match
```

**Checks**: PK overlap percentage, null PK detection, record traceability

### 3. Relationship Integrity

Validates foreign key references exist in parent tables. Detects orphaned records and null foreign keys.

```yaml
relationships:
  - child:
      table: orders
      fk_column: user_id
    parent:
      table: customers
      pk_column: id
      target: data/target/customers.csv
```

**Checks**: Foreign key constraint validation, orphaned record detection, referential integrity

### 4. Aggregate Consistency

Compares sums, counts, averages, min/max of numeric columns with percentage drift thresholds.

```yaml
aggregates:
  - amount
  - quantity
tolerances:
  aggregate_pct_diff: 1.0  # Max 1% drift allowed
```

**Checks**: SUM, AVG, MIN, MAX, VARIANCE for numeric columns

### 5. Mapping & Transformation Validity

Validates enum, status, and code transformations against allowed value lists. Includes distribution checks for categorical data.

```yaml
enum_columns:
  - column: status
    mapping: {NEW: NEW, PROCESSING: PROCESSING, SHIPPED: SHIPPED}
    check_distribution: true
    distribution_tolerance_pct: 0.05
```

**Checks**: Valid enum values, enum equivalence, categorical distribution, mapping accuracy

### 6. Data Constraints ⭐ (New)

Enforces not-null rules, date format validity, positive/range constraints, and data type validation.

```yaml
data_constraints:
  email: [not_null]
  age: [positive, between_0_150]
  created_at: [not_null, date]
```

**Checks**: NOT NULL, POSITIVE, BETWEEN ranges, date format, type consistency

### 7. String Data Quality ⭐ (New)

Detects truncation, whitespace corruption, and encoding issues in text fields.

```yaml
string_columns:
  - column: product_name
    max_length: 255
    check_whitespace: true
    check_encoding: true
```

**Checks**: Truncation detection, whitespace corruption (leading/trailing spaces), UTF-8 encoding validation

### 8. Datetime & Timezone Consistency ⭐ (New)

Validates timezone awareness, handles DST transitions, and checks timestamp consistency.

```yaml
datetime_columns:
  - column: created_at
    expected_tz: UTC
  - column: updated_at
    expected_tz: null  # Nullable TZ
```

**Checks**: Timezone consistency, null datetime handling, timestamp ordering

### 9. Null & Sentinel Equivalence ⭐ (New)

Treats null sentinels (empty strings, "N/A", "-", "null") as equivalent to actual NULLs.

```yaml
null_sentinels:
  - column: customer_notes
    sentinels: ['', 'N/A', '-', 'null', 'NO DATA']
  - column: internal_notes
    sentinels: ['']
```

**Checks**: Sentinel recognition, equivalence mapping, null handling consistency

### 10. Boolean Normalization ⭐ (New)

Validates True/False representations (1/0, Y/N, true/false, yes/no) and detects invalid boolean values.

```yaml
boolean_columns:
  - column: is_premium
    true_values: [true, 1, Y, yes]
    false_values: [false, 0, N, no]
```

**Checks**: Valid boolean values, representation consistency, invalid boolean detection

### 11. Numeric Precision ⭐ (New)

Validates decimal places, significant digits, and precision loss (e.g., 0.1234 → 0.1).

```yaml
numeric_precision_columns:
  - column: discount_rate
    expected_precision: 5    # Total digits
    expected_scale: 4        # Decimal places
```

**Checks**: Precision loss detection, scale/decimal validation, numeric truncation

### 12. Uniqueness Constraints ⭐ (New)

Detects duplicate values in columns that should be unique (transaction IDs, UUIDs, etc.).

```yaml
unique_columns:
  - transaction_hash
  - order_uuid
```

**Checks**: Duplicate detection, uniqueness enforcement

### 13. Incremental & Large-File Processing ⭐ (New)

Automatically chunks large CSVs/database queries to avoid memory exhaustion. Configured via:

```yaml
large_file_threshold_mb: 100     # Auto-enable chunking if file > 100MB
chunk_size: 50000                # Process in 50K row chunks
```

**Checks**: Streamed aggregation, chunked identity/volume validation, memory-efficient processing

## Output & Verdict

### Check Statuses

| Status     | Meaning                             |
| ---------- | ----------------------------------- |
| **PASS** ✓ | Validation successful               |
| **WARN** ⚠ | Minor deviation within tolerance    |
| **FAIL** ✗ | Critical issue blocking deployment  |
| **ERROR**  | Check crashed (isolated, non-fatal) |

### Final Verdict

| Condition          | Verdict              | Action                          |
| ------------------ | -------------------- | ------------------------------- |
| Any FAIL detected  | **NO-GO**            | Do not deploy. Investigate.     |
| Only WARN detected | **GO WITH WARNINGS** | Deploy with documented caveats. |
| All PASS           | **GO**               | Safe to deploy immediately.     |

### Report Formats

| Format   | File                | Purpose                  |
| -------- | ------------------- | ------------------------ |
| HTML     | `Audit_Report.html` | Interactive web report   |
| PDF      | `Audit_Report.pdf`  | Printable executive copy |
| Markdown | `Audit_Report.md`   | GitHub-compatible        |
| JSON     | `Audit_Report.json` | Machine-readable API     |

## Project Structure

```
albatross/
├── albatross_pro/             # Premium Module (Auth, Compliance, Web, Sanitization)
│   ├── auth/                  # RBAC, SSO, License Management
│   ├── compliance/            # Audit Trail, Retention, Reporting
│   ├── sanitization/          # PII Masking & Data Redaction
│   └── web/                   # FastAPI Web Dashboard & API
├── albatross_docs/            # Project Documentation & Architecture
├── core/                      # Open Core Audit Engine
│   ├── audit/                 # Execution, Config, Verdicts, Logging
│   ├── db/                    # Multi-source Data Loading (CSV/SQL)
│   ├── notifications/         # Webhook & Alert Dispatchers
│   └── schema_only/           # Metadata-only validation
├── checks/                    # 5-Dimension Validation Plugins
├── config/                    # Migration configurations (audit.yaml)
├── reports/                   # Open Core JSON Report Builder
├── tests/                     # Core Test Suite
├── run_audit.py               # CLI Orchestrator
└── cli.py                     # Command-line interface
├── Dockerfile                 # Multi-stage Docker build
├── docker-compose.yml         # Container orchestration
├── requirements.txt           # Python dependencies
└── debug_data.py              # Data exploration tool
```

## Configuration

All audits are **config-driven** through `config/audit.yaml`. No code modifications needed.

| Section            | Purpose                                                  |
| ------------------ | -------------------------------------------------------- |
| `tables`           | Source/target data paths, primary keys, mapping types    |
| `aggregates`       | Numeric columns for total validation                     |
| `data_constraints` | Not-null, date format, data type rules                   |
| `mappings`         | Allowed values for enum/status/code columns              |
| `relationships`    | Foreign key and referential integrity rules              |
| `tolerances`       | Acceptable thresholds (volume loss %, aggregate drift %) |

### Database Sources (New)

Data can now be loaded from databases instead of CSV files using the `DataSource` abstraction:

```python
from core.db.data_source import create_data_source

# CSV source
csv = create_data_source("data/source/users.csv")

# Database source
db = create_data_source("postgresql://user:pass@host/db", table_name="users")

df = csv.load()  # Returns pandas DataFrame
```

Supported databases: **PostgreSQL**, **MySQL**, **SQLite**, **SQL Server**, **Oracle**.

## Testing

```bash
# Run full test suite
python3 -m pytest tests/ -v

# Run with coverage
python3 -m pytest tests/ --cov=core --cov=checks -v

# Run specific test module
python3 -m pytest tests/test_data_source.py -v
```

**Current status**: 82 tests passing across all modules.

## Design Decisions

Architecture Decision Records (ADRs) are maintained in `.antigravity/context/decisions/`:

| ADR     | Decision                                                   |
| ------- | ---------------------------------------------------------- |
| ADR-001 | **SQLAlchemy** for database abstraction (over raw drivers) |
| ADR-002 | **Chart.js** for dashboard visualization (over Plotly, D3) |
| ADR-003 | **OIDC** for SSO integration (over SAML 2.0)               |

## Design Principles

1. **Config-Driven Architecture** — All validation rules in `audit.yaml`. No code changes between migrations
2. **Graceful Error Isolation** — Every check wrapped in `_safe_run()`. One crash doesn't block others
3. **Unified Data Abstraction** — CSV and database sources share the same `DataSource` interface
4. **Defense in Depth** — Null guards, type checks, and DataFrame validation at every boundary
5. **Business-First Reporting** — Clear GO/NO-GO verdicts. No technical jargon for executives
6. **Deterministic & Reproducible** — Identical inputs always produce identical results

## What This Tool Is NOT

- ❌ **Migration execution framework** — Doesn't move data, only validates
- ❌ **Performance benchmarking tool** — Doesn't measure speed or resources
- ❌ **Schema redesign utility** — Doesn't modify table structures
- ❌ **Data quality enrichment pipeline** — Doesn't clean or transform data
- ❌ **Continuous monitoring system** — Validates at a point-in-time, not ongoing

## Roadmap

### In Progress (Sprint 1)

- [x] Multi-stage Docker build with health checks
- [x] Core audit hardening (error isolation, null guards)
- [x] DataSource abstraction (CSV + database)
- [x] Web dashboard redesign (drag-and-drop, SSE progress)
- [x] AI/ML opportunity analysis
- [x] Auth/RBAC security design
- [x] Compliance framework (SOC 2 Type II)

### Planned

- [ ] OIDC single sign-on integration
- [ ] Chart.js dashboard visualizations (pass/fail charts, trends)
- [ ] Streaming/chunked processing for large files (>100MB)
- [ ] Aggregate anomaly detection (Z-score / Isolation Forest)
- [ ] Auto-tolerance calibration
- [ ] PII auto-detection (regex + optional NER)
- [ ] Immutable audit trail with hash chain
- [ ] Data retention lifecycle management
- [ ] CI/CD pipeline integration (audit as deployment gate)

## License

This project is licensed under the **GNU General Public License v3.0 (GPLv3)**. See the [LICENSE](LICENSE) file for the full license text.

---

**For feedback or contributions**, please open an issue or submit a pull request on the GitHub repository.
