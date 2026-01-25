# Migration Validation & Risk Audit Framework

A production-grade, configuration-driven data migration audit framework that validates correctness, integrity, and deployment readiness of data migrations across multiple dimensions.

**Core Question:** Is the migrated system safe to deploy?

## 📋 Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Validation Dimensions](#validation-dimensions)
- [Output & Verdict](#output--verdict)
- [Project Structure](#project-structure)
- [Design Principles](#design-principles)
- [What This Tool Is NOT](#what-this-tool-is-not)
- [Use Cases](#use-cases)
- [Future Enhancements](#future-enhancements)

## Overview

This tool provides a standardized, reusable framework for auditing data migrations against five critical validation dimensions. It produces a clear **GO / GO WITH WARNINGS / NO-GO** deployment verdict based on configurable business rules and tolerance thresholds.

### Key Strengths

- **No hardcoding**: All table names, columns, and tolerances are defined in a single YAML configuration file
- **Production-ready**: Designed for enterprise-grade migration validation
- **Reproducible**: Identical inputs always produce identical results
- **Business-focused**: Reports map directly to executive-readable audit conclusions

## Key Features

| Feature | Description |
|---------|-------------|
| **Volume Integrity** | Validates complete data migration within acceptable loss tolerance |
| **Relationship Integrity** | Verifies foreign key constraints and prevents orphaned records |
| **Aggregate Consistency** | Confirms counts, sums, and statistics match source system |
| **Mapping Validation** | Validates enum, status, and code transformations |
| **Data Constraints** | Enforces not-null, date format, and data type validations |
| **Automated Verdicts** | Generates deployment-ready GO/NO-GO decisions |

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Step 1: Create Virtual Environment

```bash
# On Linux / macOS
python -m venv venv
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
python -c "import pandas; import yaml; print('✓ Dependencies installed successfully')"
```

## Configuration

All audits are **config-driven** through a single YAML file. No code modifications are required to audit different migrations.

### Configuration File: `config/audit.yaml`

Edit `config/audit.yaml` to define your audit rules. This is the **only file** that needs to be changed between different migrations or clients.

The configuration includes these main sections:

| Section | Purpose |
|---------|---------|
| `tables` | Define source and target data file paths and primary keys for each table |
| `aggregates` | Specify numeric columns whose totals should be validated |
| `data_constraints` | Define validation rules (e.g., not_null, date format, data types) |
| `mappings` | Specify allowed values for enum/status/code columns |
| `relationships` | Define foreign key and referential integrity rules |
| `tolerances` | Set acceptable thresholds (e.g., volume loss %, aggregate drift %) |

Refer to the sample configuration in `config/audit.yaml` for the complete structure and syntax.

## Usage

### Running an Audit

```bash
# Basic audit execution
python run_audit.py

# With debug output (optional)
python debug_data.py
```

### What Happens During Audit

1. **Load Configuration**: Reads `config/audit.yaml`
2. **Load Datasets**: Reads source and target CSV files
3. **Execute Checks**: Runs all validation checks across five dimensions
4. **Aggregate Results**: Collects check results by severity
5. **Compute Verdict**: Determines GO/NO-GO/GO WITH WARNINGS
6. **Generate Reports**: Produces structured audit reports

### Output Files

The audit generates multiple output formats:

| File | Format | Purpose |
|------|--------|---------|
| `audit_report.txt` | Plain text | Human-readable summary |
| `audit_report.md` | Markdown | GitHub-compatible report |
| `audit_report.json` | JSON | Machine-readable results |

## Validation Dimensions

### 1. Volume Integrity (Completeness Check)

**Purpose**: Ensures all intended data has been migrated

- Compares record counts: source vs. target
- Calculates data loss percentage
- Verdict: PASS if within tolerance, FAIL otherwise

**Configuration**:
```yaml
tolerances:
  volume_loss_pct: 0.1  # Max 0.1% loss allowed
```

### 2. Relationship Integrity (Foreign Key Check)

**Purpose**: Verifies all relationships between business objects are preserved

- Validates foreign key references exist in parent table
- Detects orphaned records (missing parent records)
- Confirms no broken links

**Configuration**:
```yaml
relationships:
  - child:
      target: data/target/orders.csv
      fk_column: user_id
      parent_table: users
```

### 3. Aggregate Consistency (Business Totals Check)

**Purpose**: Confirms key business metrics match source system

- Compares sums and counts of numeric columns
- Calculates percentage drift
- Ensures business logic is preserved

**Configuration**:
```yaml
aggregates:
  - amount
  - quantity
tolerances:
  aggregate_drift_pct: 1.0
```

### 4. Mapping & Transformation Validity (Code Mapping Check)

**Purpose**: Validates enum, status, and code transformations

- Ensures only allowed values appear in mapped columns
- Detects invalid or missing code transformations
- Validates boolean conversions

**Configuration**:
```yaml
mappings:
  - columns: [status, order_status]
    allowed_values: [active, inactive, pending, completed]
```

### 5. Data Constraints (Constraint Check)

**Purpose**: Enforces data quality rules

- Validates not-null constraints
- Checks date format validity
- Detects data type mismatches
- Enforces business-specific rules

**Configuration**:
```yaml
data_constraints:
  email: [not_null]
  birth_date: [not_null, date]
  status: [not_null]
```

## Output & Verdict

### Check Results

Each validation check produces one of three outcomes:

| Result | Meaning | Action |
|--------|---------|--------|
| **PASS** ✓ | Validation successful, no issues | No action needed |
| **WARN** ⚠️ | Minor deviation detected within tolerance | Review findings, proceed with caution |
| **FAIL** ✗ | Critical issue blocking deployment | Stop migration, investigate root cause |

### Final Verdict

The overall deployment verdict is determined by aggregating all check results:

| Condition | Verdict | Recommendation |
|-----------|---------|-----------------|
| Any FAIL detected | **NO-GO** | Do not deploy. Investigate failures. |
| Only WARN detected | **GO WITH WARNINGS** | Safe to deploy with documented caveats. |
| All PASS | **GO** | Safe to deploy immediately. |

### Sample Report Output

```
╔════════════════════════════════════════════════════════════╗
║           MIGRATION AUDIT RESULTS - FINAL VERDICT          ║
╠════════════════════════════════════════════════════════════╣
║ OVERALL VERDICT: GO WITH WARNINGS                          ║
║ ─────────────────────────────────────────────────────────  ║
║ ✓ Volume Integrity:        PASS (0.05% loss)              ║
║ ⚠ Relationship Integrity:  WARN (2 orphaned records)      ║
║ ✓ Aggregate Consistency:   PASS (0.8% variance)            ║
║ ✓ Mapping Validation:      PASS (all codes valid)          ║
║ ✓ Data Constraints:        PASS (no violations)            ║
╚════════════════════════════════════════════════════════════╝
```

## Project Structure

```
migration_audit-main/
├── README.md                          # This file
├── requirements.txt                   # Python dependencies
├── config/
│   └── audit.yaml                    # Configuration (THE ONLY FILE TO EDIT)
├── data/
│   ├── source/                       # Source CSV files
│   │   ├── users.csv
│   │   ├── orders.csv
│   │   └── ...
│   └── target/                       # Target CSV files
│       ├── users.csv
│       ├── orders.csv
│       └── ...
├── core/                              # Core audit framework
│   ├── check_registry.py             # Check registration system
│   ├── check_runner.py               # Audit execution engine
│   ├── config_models.py              # Configuration data models
│   ├── enums.py                      # Constants and enumerations
│   ├── exceptions.py                 # Custom exceptions
│   ├── loader.py                     # Data loading utilities
│   ├── logger.py                     # Logging configuration
│   ├── result.py                     # Result data structures
│   └── verdict.py                    # Verdict computation logic
├── checks/                            # Validation checks
│   ├── volume.py                     # Volume integrity check
│   ├── relationships.py              # Relationship integrity check
│   ├── aggregates.py                 # Aggregate consistency check
│   ├── mappings.py                   # Mapping validation check
│   └── data_constraints.py           # Data constraint validation
├── reports/                           # Report generation
│   ├── report_builder.py             # Main report generator
│   └── table_audit_result.py         # Table result formatting
├── tests/                             # Unit tests
│   ├── test_volume.py
│   ├── test_relationships.py
│   ├── test_aggregates.py
│   ├── test_mappings.py
│   └── test_data_constraints.py
├── run_audit.py                      # Main execution script
└── debug_data.py                     # Debug and exploration tool
```

## Design Principles

### 1. **Config-Driven Architecture**
All validation rules are defined in `config/audit.yaml`. No Python code changes needed to audit different migrations or adjust tolerances. This enables reuse across clients and migration projects.

### 2. **One-Size-Fits-All Structure**
The audit questions never change—only inputs do. Every migration uses the same five validation dimensions, ensuring consistency and predictability.

### 3. **Deterministic & Reproducible**
Identical configuration and data inputs always produce identical results. No randomness, no floating-point surprises. Perfect for compliance and audit trails.

### 4. **Business-First Reporting**
Results map directly to business-readable conclusions. Executives receive clear GO/NO-GO verdicts without technical jargon.

### 5. **Production-Grade Robustness**
Handles edge cases, null values, type mismatches, and data quality issues gracefully. Designed for real-world messy data.

## What This Tool Is NOT

This tool is **not** a replacement for:

- ❌ **Migration execution framework**: Doesn't move data, only validates
- ❌ **Performance benchmarking tool**: Doesn't measure speed or resource usage
- ❌ **Schema redesign utility**: Doesn't modify table structures
- ❌ **Data quality enrichment pipeline**: Doesn't clean or transform data
- ❌ **Continuous monitoring system**: Validates at a point-in-time, not ongoing

This tool validates correctness and deployment readiness, not implementation.

## Use Cases

### 1. Pre-Production Migration Validation
Audit data before go-live to ensure system integrity.

### 2. Third-Party Migration Verification
Independently verify migrations executed by external vendors or consultants.

### 3. Regulatory & Compliance Audits
Generate documented evidence of data migration correctness for compliance bodies.

### 4. Executive Sign-Off for Deployment
Provide clear GO/NO-GO verdicts for deployment decision-makers.

### 5. Multi-Environment Migration
Validate migrations across dev → staging → production with consistent rules.

## Future Enhancements

Potential improvements for future versions:

- [ ] **Interactive CLI**: Command-line interface for environment selection and report format choice
- [ ] **Automated Report Generation**: DOCX/PDF export with executive summaries
- [ ] **Audit Trail & Logging**: Complete activity logs for compliance
- [ ] **Database Support**: Extend beyond CSV to SQL databases (PostgreSQL, MySQL, SQL Server)
- [ ] **CI/CD Integration**: Embed audit as deployment gate in pipeline
- [ ] **Data Lineage**: Track data transformations across migration
- [ ] **Anomaly Detection**: AI-powered detection of unexpected patterns
- [ ] **Real-Time Validation**: Stream validation during migration execution

## License

Internal / Client-specific usage.

---

**For questions or support**, refer to sample documentation in `sample_data_docs/` directory.