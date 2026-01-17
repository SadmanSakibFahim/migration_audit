# Migration Validation & Risk Audit

A config-driven, production-grade data migration audit framework that validates correctness, integrity, and deployability of data migrations.

This tool answers one core question:

Is the migrated system safe to deploy?

It does so by running a standardized set of validation checks and producing a clear GO / GO WITH WARNINGS / NO-GO verdict.

## What This Tool Does

The audit validates data migrations across five invariant dimensions:

Data Completeness (Volume Integrity)
Ensures all intended data has been migrated within acceptable tolerance.

Relationship Integrity (Object Linkage)
Verifies that relationships between business objects are preserved (no orphans, no broken links).

Aggregate Consistency (Business Totals)
Confirms that key aggregates (counts, sums, statistics) match the source system within defined tolerance.

Mapping & Transformation Validity
Validates that enums, statuses, booleans, and code mappings were applied correctly.

Deployability Verdict
Produces a final deployment decision based on all findings.

### Installation
1. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate      # Linux / macOS
venv\Scripts\activate         # Windows

2. Install dependencies
pip install -r requirements.txt

Configuration

All audits are config-driven.
No table names, columns, or tolerances are hardcoded.

Example: config/audit.yaml
tables:
  users:
    source: data/source/users.csv
    target: data/target/users.csv
    primary_key: user_id

  orders:
    source: data/source/orders.csv
    target: data/target/orders.csv
    primary_key: order_id
    foreign_keys:
      user_id: users.user_id

tolerances:
  volume_loss_pct: 0.1
  aggregate_drift_pct: 1.0


Only this file changes between clients.

Running an Audit
Basic execution
python run_audit.py


### This will:

Load source and target datasets

Execute all configured checks

Produce structured audit results

Compute a final deployment verdict

### Output

Each check produces a standardized result object:

PASS — validation successful

WARN — acceptable deviation detected

FAIL — deployment-blocking issue detected

### The final verdict is derived from these results:

Condition	Verdict
Any FAIL	NO-GO
Only WARN	GO WITH WARNINGS
All PASS	GO

## Design Principles

### One-size-fits-all audit structure
The audit questions never change. Only inputs do.

### Config-driven
Enables reuse across clients and migrations.

### Deterministic & reproducible
Same inputs always produce the same results.

### Business-first reporting
Results map directly to executive-readable audit reports.

## hat This Tool Is NOT

A migration execution framework

A performance benchmarking tool

A schema redesign utility

A data quality enrichment pipeline

This tool validates correctness and readiness, not implementation.

## Typical Use Cases

Pre-production migration validation

Third-party migration verification

Regulatory or compliance-driven audits

Executive sign-off for deployment readiness

## Next Steps (Optional Enhancements)

CLI interface for multiple environments

Automated DOCX / PDF report generation

Logging and audit trail

Support for databases beyond CSV

CI/CD integration for migration gates

License

Internal / Client-specific usage.