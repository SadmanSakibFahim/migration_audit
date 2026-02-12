# Migration Validation & Risk Audit Framework

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

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     Web Dashboard (Vue.js)                    │
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

### CLI Audit

```bash
# Run audit on all configured tables
python3 run_audit.py

# Run audit on specific tables
python3 run_audit.py --tables users orders

# Debug data exploration
python3 debug_data.py
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

### Starting the Dashboard

```bash
uvicorn core.web.app:app --host 0.0.0.0 --port 8000 --reload
```

Then open [http://localhost:8000](http://localhost:8000) in your browser.

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
docker compose ps
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

### 1. Volume Integrity

Compares record counts between source and target. Supports 1:N and N:1 mapping types with configurable tolerance.

```yaml
tolerances:
  volume_loss_pct: 0.1 # Max 0.1% loss allowed
```

### 2. Relationship Integrity

Validates foreign key references exist in parent tables. Detects orphaned records and null foreign keys.

```yaml
relationships:
  - child:
      target: data/target/orders.csv
      fk_column: user_id
      parent_table: users
```

### 3. Aggregate Consistency

Compares sums, counts, averages, min/max of numeric columns with percentage drift thresholds.

```yaml
aggregates:
  - amount
  - quantity
tolerances:
  aggregate_drift_pct: 1.0
```

### 4. Mapping & Transformation Validity

Validates enum, status, and code transformations against allowed value lists.

```yaml
mappings:
  - columns: [status, order_status]
    allowed_values: [active, inactive, pending, completed]
```

### 5. Data Constraints

Enforces not-null rules, date format validity, and data type checks.

```yaml
data_constraints:
  email: [not_null]
  birth_date: [not_null, date]
```

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
migration_audit/
├── config/
│   └── audit.yaml                     # Audit configuration (ONLY file to edit per migration)
├── core/
│   ├── audit/                         # Core audit engine
│   │   ├── check_runner.py            # Execution with _safe_run() and _validate_dataframes()
│   │   ├── config_models.py           # Pydantic configuration models
│   │   ├── loader.py                  # Data loading utilities
│   │   ├── verdict.py                 # Verdict computation
│   │   ├── result.py                  # TestResult data structures
│   │   └── logger.py                  # Logging configuration
│   ├── db/                            # Database abstraction layer
│   │   ├── data_source.py             # DataSource ABC + CSV + Database implementations
│   │   ├── drivers.py                 # Database driver detection and validation
│   │   └── exceptions.py              # DatabaseConnectionError, DatabaseQueryError
│   ├── web/                           # Web dashboard
│   │   ├── app.py                     # FastAPI application + security middleware
│   │   ├── routes/
│   │   │   └── api.py                 # REST API endpoints (upload, audit, stream, reports)
│   │   ├── templates/
│   │   │   └── dashboard.html         # Vue.js dashboard with wizard UI
│   │   └── static/js/
│   │       └── app.js                 # Frontend application logic
│   ├── auth/                          # Authentication & authorization
│   │   └── service.py                 # AuthService with Argon2 hashing
│   └── sanitization/                  # PII/data masking
│       └── masking.py                 # DataSanitizer (SHA-256 hashing, column dropping)
├── checks/                            # 5-dimension validation checks
│   ├── volume.py                      # Volume integrity (row count comparison)
│   ├── relationships.py               # Referential integrity (FK validation)
│   ├── aggregates.py                  # Aggregate consistency (sum/avg/min/max)
│   ├── mappings.py                    # Mapping validation (allowed values)
│   └── data_constraints.py            # Data constraints (not_null, date format)
├── reports/                           # Report generation
│   ├── report_builder.py              # Multi-format report generator
│   └── table_audit_result.py          # Table result formatting
├── scripts/
│   └── smoke_test.sh                  # Docker container health validation
├── tests/                             # Test suite (82 tests)
│   ├── test_data_source.py            # DataSource abstraction tests (20 tests)
│   ├── test_volume.py                 # Volume check tests
│   ├── test_relationships.py          # Relationship check tests
│   ├── test_mappings.py               # Mapping check tests
│   ├── test_data_constraints.py       # Constraint check tests
│   ├── test_auth_service.py           # Auth service tests
│   ├── test_compliance.py             # Security/compliance tests
│   └── test_db_integration.py         # Database integration tests
├── docs/                              # Design documentation
│   ├── AI_ML_OPPORTUNITIES.md         # ML augmentation analysis
│   ├── AUTH_SECURITY_DESIGN.md        # Auth & RBAC design
│   ├── COMPLIANCE_FRAMEWORK.md        # SOC 2 / GDPR compliance plan
│   └── EDGE_CASE_CATALOG.md           # Known edge cases & remediation
├── Dockerfile                         # Multi-stage Docker build
├── docker-compose.yml                 # Container orchestration
├── requirements.txt                   # Python dependencies
├── run_audit.py                       # CLI entry point
└── debug_data.py                      # Data exploration tool
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

Internal / Client-specific usage.

---

**For questions or support**, refer to documentation in the `docs/` directory.
