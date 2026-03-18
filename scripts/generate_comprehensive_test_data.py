#!/usr/bin/env python3
"""
Comprehensive test data generator for exercising ALL checks in the audit engine.

This script generates source and target datasets that:
- Exercise every check type (13+)
- Include all complexity scenarios (enums, strings, datetimes, nulls, constraints, etc.)
- Randomly fail a percentage of checks to create realistic mixed results
- Generate valid YAML config to tie it all together
"""

import argparse
import os
import random
import string
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd
import yaml

# Seeds for reproducibility if desired (leave None for nondeterministic output)
RANDOM_SEED = None


def set_seed(seed: Optional[int] = RANDOM_SEED):
    """Set RNG seed for reproducibility."""
    if seed is not None:
        random.seed(seed)
        import numpy as np
        np.random.seed(seed)


def generate_base_row(row_id: int, fail_rate: float = 0.3) -> Dict[str, Any]:
    """Generate a single row that may have various types of issues."""
    # Primary key always exists
    row = {
        "id": row_id,
        "order_id": f"ORD-{row_id:06d}",
    }
    
    # Volume field (subject to potential volume mismatch)
    row["quantity"] = random.randint(1, 100)
    
    # Aggregates (sum/average/min/max fields)
    row["price_usd"] = round(random.uniform(1.0, 5000.0), 2)
    row["subtotal"] = round(row["quantity"] * row["price_usd"], 2)
    
    # String fields (truncation, encoding, whitespace checks)
    row["product_name"] = "".join(random.choices(string.ascii_letters + " ", k=random.randint(5, 200)))
    row["description"] = "Product " + str(row_id)
    
    # Enum/categorical field
    row["status"] = random.choice(["NEW", "PROCESSING", "SHIPPED", "DELIVERED", "CANCELLED"])
    row["payment_method"] = random.choice(["CARD", "BANK", "PAYPAL", "CRYPTO"])
    
    # Boolean field
    row["is_premium"] = random.choice([True, False, 1, 0, "Y", "N"])  # Various representations
    
    # Datetime field with timezone awareness
    base_date = datetime.now() - timedelta(days=random.randint(0, 365))
    row["created_at"] = base_date
    row["updated_at"] = base_date + timedelta(hours=random.randint(0, 720))
    
    # Null sentinels & NULL handling
    row["customer_notes"] = random.choice([None, "", "N/A", "-", "null", "NO DATA", f"Note {row_id}"])
    row["internal_notes"] = random.choice([None, f"Internal {row_id}"])
    
    # Numeric precision field
    row["discount_rate"] = round(random.uniform(0.0, 0.5), 4) if random.random() > 0.2 else None
    
    # Unique field
    row["transaction_hash"] = f"TXN-{row_id}-{random.randint(10000, 99999)}"
    
    # Fields for relationship checks (foreign keys)
    row["customer_id"] = random.randint(1, 100)
    row["warehouse_id"] = random.choice([1, 2, 3, 4, 5, None])
    
    return row


def apply_random_failures(row: Dict[str, Any], fail_rate: float = 0.3) -> Dict[str, Any]:
    """Apply random data quality issues to a row."""
    if random.random() > fail_rate:
        return row  # No failure in this row
    
    # Apply one or more failures
    num_failures = random.randint(1, 3)
    for _ in range(num_failures):
        failure_type = random.choice([
            "truncate_string",
            "corrupt_encoding",
            "corrupt_whitespace",
            "wrong_enum",
            "bad_boolean",
            "null_violation",
            "precision_loss",
            "volume_mismatch",
            "missing_relationship_key",
        ])
        
        if failure_type == "truncate_string" and "product_name" in row:
            row["product_name"] = row["product_name"][:5] + "..."  # Simulate truncation
            
        elif failure_type == "corrupt_encoding" and "product_name" in row:
            row["product_name"] = row["product_name"].encode('utf-8', errors='replace').decode('utf-8')
            
        elif failure_type == "corrupt_whitespace" and "product_name" in row:
            row["product_name"] = "  " + row["product_name"] + "  "  # Extra spaces
            
        elif failure_type == "wrong_enum" and "status" in row:
            row["status"] = random.choice(["INVALID", "UNKNOWN", "PENDING", "LOST"])
            
        elif failure_type == "bad_boolean" and "is_premium" in row:
            row["is_premium"] = random.choice(["maybe", "UNKNOWN", "2", ""])
            
        elif failure_type == "null_violation" and random.random() > 0.5:
            col_to_null = random.choice(["customer_id", "created_at"])
            if col_to_null in row:
                row[col_to_null] = None
                
        elif failure_type == "precision_loss" and "discount_rate" in row and row["discount_rate"] is not None:
            row["discount_rate"] = round(row["discount_rate"], 1)  # Lose precision
            
        elif failure_type == "volume_mismatch" and "quantity" in row:
            row["quantity"] = random.randint(101, 200)  # Different from source
            
        elif failure_type == "missing_relationship_key" and "customer_id" in row:
            row["customer_id"] = random.randint(1000, 2000)  # Non-existent customer
    
    return row


def generate_source_data(num_rows: int = 100, fail_rate: float = 0.2) -> pd.DataFrame:
    """Generate clean source data."""
    rows = []
    for i in range(1, num_rows + 1):
        row = generate_base_row(i, fail_rate=0)  # Source is clean
        rows.append(row)
    
    df = pd.DataFrame(rows)
    return df


def generate_target_data(num_rows: int = 100, fail_rate: float = 0.3) -> pd.DataFrame:
    """Generate target data with random failures."""
    rows = []
    for i in range(1, num_rows + 1):
        row = generate_base_row(i, fail_rate=0)
        row = apply_random_failures(row, fail_rate=fail_rate)
        rows.append(row)
    
    df = pd.DataFrame(rows)
    return df


def generate_audit_config() -> Dict[str, Any]:
    """Generate a comprehensive audit.yaml config that references all check types."""
    config = {
        "tables": {
            "orders": {
                "source": "random_data/source/orders.csv",
                "target": "random_data/target/orders.csv",
                "primary_key": "id",
                "volume_tolerance": 0.1,
                "aggregate_tolerance": 1.0,
                "identity_overlap_threshold": 95,
                
                # String columns with all string check variants
                "string_columns": [
                    {
                        "column": "product_name",
                        "max_length": 255,
                        "check_whitespace": True,
                        "check_encoding": True,
                    },
                    {
                        "column": "description",
                        "max_length": 500,
                        "check_whitespace": False,
                        "check_encoding": True,
                    },
                ],
                
                # Enum columns with all enum check variants
                "enum_columns": [
                    {
                        "column": "status",
                        "mapping": {"NEW": "NEW", "PROCESSING": "PROCESSING", "SHIPPED": "SHIPPED", "DELIVERED": "DELIVERED", "CANCELLED": "CANCELLED"},
                        "check_distribution": True,
                        "distribution_tolerance_pct": 0.05,
                    },
                    {
                        "column": "payment_method",
                        "mapping": {"CARD": "CARD", "BANK": "BANK", "PAYPAL": "PAYPAL", "CRYPTO": "CRYPTO"},
                        "check_distribution": False,
                    },
                ],
                
                # Boolean columns
                "boolean_columns": [
                    {
                        "column": "is_premium",
                        "true_values": ["true", "1", "Y", "yes"],
                        "false_values": ["false", "0", "N", "no"],
                    },
                ],
                
                # Datetime columns with timezone checks
                "datetime_columns": [
                    {
                        "column": "created_at",
                        "expected_tz": "UTC",
                    },
                    {
                        "column": "updated_at",
                        "expected_tz": None,
                    },
                ],
                
                # Null sentinels
                "null_sentinels": [
                    {
                        "column": "customer_notes",
                        "sentinels": ["", "N/A", "-", "null", "NO DATA"],
                    },
                    {
                        "column": "internal_notes",
                        "sentinels": [""],
                    },
                ],
                
                # Numeric precision fields
                "numeric_precision_columns": [
                    {
                        "column": "discount_rate",
                        "expected_precision": 5,  # Total digits
                        "expected_scale": 4,  # Decimal places
                    },
                    {
                        "column": "price_usd",
                        "expected_precision": 8,
                        "expected_scale": 2,
                    },
                ],
                
                # Aggregates (for SUM, AVG, etc.)
                "aggregates": ["subtotal", "price_usd", "quantity"],
                
                # Unique constraints
                "unique_columns": ["transaction_hash"],
                
                # Data constraints by column
                "data_constraints": {
                    "quantity": ["positive"],
                    "discount_rate": ["between_0_1"],
                    "customer_id": ["not_null"],
                },
                
                # Mappings (simple value transformations)
                "mappings": [
                    {
                        "columns": ["status"],
                        "allowed_values": ["NEW", "PROCESSING", "SHIPPED", "DELIVERED", "CANCELLED"],
                    },
                ],
                
                # Relationships (foreign keys)
                "relationships": [
                    {
                        "child": {"table": "orders", "fk_column": "customer_id"},
                        "parent": {"table": "customers", "pk_column": "id", "target": "random_data/target/customers.csv"},
                    },
                    {
                        "child": {"table": "orders", "fk_column": "warehouse_id"},
                        "parent": {"table": "warehouses", "pk_column": "id", "target": "random_data/target/warehouses.csv"},
                    },
                ],
            },
        }
    }
    return config


def generate_reference_tables(num_rows: int = 100):
    """Generate reference tables for relationship checks."""
    # Customers ref table
    customer_rows = [{"id": i, "name": f"Customer {i}"} for i in range(1, num_rows + 1)]
    customers_df = pd.DataFrame(customer_rows)
    
    # Warehouses ref table
    warehouse_rows = [{"id": i, "name": f"Warehouse {i}"} for i in range(1, 6)]
    warehouses_df = pd.DataFrame(warehouse_rows)
    
    return customers_df, warehouses_df


def display_expected_errors(fail_rate: float = 0.35, num_rows: int = 150):
    """Display what data quality errors will be generated in the test dataset."""
    print("\n" + "="*80)
    print("EXPECTED DATA QUALITY ERRORS TO BE GENERATED")
    print("="*80)
    
    num_failing_rows = int(num_rows * fail_rate)
    avg_errors_per_row = 2  # Since we apply 1-3 random failures per failing row
    total_expected_errors = num_failing_rows * avg_errors_per_row
    
    print(f"\nGeneration Configuration:")
    print(f"  • Total rows: {num_rows}")
    print(f"  • Failure rate: {fail_rate*100:.0f}%")
    print(f"  • Expected failing rows: ~{num_failing_rows} rows")
    print(f"  • Avg errors per row: 1-3 (expect ~{total_expected_errors} total errors)")
    
    print(f"\nError Types That Will Appear:")
    print(f"  1. [STRING TRUNCATION] product_name truncated to 8 chars + '...'")
    print(f"     → Fails: String Truncation Check")
    print(f"     → Expected in ~{int(num_failing_rows/9)} rows")
    
    print(f"\n  2. [ENCODING CORRUPTION] product_name with UTF-8 replacement chars")
    print(f"     → Fails: Encoding Corruption Check")
    print(f"     → Expected in ~{int(num_failing_rows/9)} rows")
    
    print(f"\n  3. [WHITESPACE CORRUPTION] product_name with extra leading/trailing spaces")
    print(f"     → Fails: Whitespace Corruption Check")
    print(f"     → Expected in ~{int(num_failing_rows/9)} rows")
    
    print(f"\n  4. [WRONG ENUM] status changed to invalid values (INVALID|UNKNOWN|PENDING|LOST)")
    print(f"     → Fails: Enum Equivalence Check, Mapping Check")
    print(f"     → Expected in ~{int(num_failing_rows/9)} rows")
    
    print(f"\n  5. [BAD BOOLEAN] is_premium set to non-boolean values (maybe|UNKNOWN|2|'')")
    print(f"     → Fails: Boolean Normalization Check")
    print(f"     → Expected in ~{int(num_failing_rows/9)} rows")
    
    print(f"\n  6. [NULL VIOLATION] customer_id or created_at set to NULL")
    print(f"     → Fails: Data Constraint Check (NOT NULL), Identity Check (NULL PKs)")
    print(f"     → Expected in ~{int(num_failing_rows/18)} rows")
    
    print(f"\n  7. [PRECISION LOSS] discount_rate rounded from .xxxx to .x (e.g., 0.1234 → 0.1)")
    print(f"     → Fails: Numeric Precision Check")
    print(f"     → Expected in ~{int(num_failing_rows/9)} rows")
    
    print(f"\n  8. [VOLUME MISMATCH] quantity increased from 1-100 to 101-200 on target")
    print(f"     → Fails: Volume Check, Aggregate Check (SUM/AVG)")
    print(f"     → Expected in ~{int(num_failing_rows/9)} rows")
    
    print(f"\n  9. [MISSING RELATIONSHIP] customer_id set to non-existent IDs (1000-2000)")
    print(f"     → Fails: Relationship Check (Foreign Key)")
    print(f"     → Expected in ~{int(num_failing_rows/9)} rows")
    
    print(f"\nAdditional Issues to Expect:")
    print(f"  • Null/Sentinel Check: customer_notes has '', 'N/A', '-', 'null', 'NO DATA'")
    print(f"  • Categorical Distribution: status distribution may vary >5% (35% target failures)")
    print(f"  • Uniqueness Check: transaction_hash should be unique (but may collide rarely)")
    print(f"  • Aggregate Issues: subtotal = quantity × price_usd (may be incorrect due to mismatches)")
    print(f"  • Datetime Checks: created_at & updated_at present but timezone may be inconsistent")
    
    print(f"\nWhen You Run: python run_audit.py --no-auth --headless")
    print(f"Expected Report Sections With Failures:")
    print(f"  ✗ String Data Quality Checks (~{int(num_failing_rows/3)} findings)")
    print(f"  ✗ Enum & Categorical Checks (~{int(num_failing_rows/4.5)} findings)")
    print(f"  ✗ Numeric Precision Checks (~{int(num_failing_rows/9)} findings)")
    print(f"  ✗ Data Constraint Checks (~{int(num_failing_rows/9)} findings)")
    print(f"  ✗ Relationship Checks (~{int(num_failing_rows/9)} findings)")
    print(f"  ✓ Identity Checks (should PASS unless NULL PKs generated)")
    print(f"  ✓ Volume Checks (source & target have same row count)")
    print(f"  ✓ Boolean Normalization (may vary depending on random failures)")
    
    print("\n" + "="*80 + "\n")


def main():
    """Main: Generate all test data and config."""
    parser = argparse.ArgumentParser(description="Generate comprehensive test data for the audit engine.")
    parser.add_argument("--seed", type=int, default=RANDOM_SEED, help="Optional random seed (omit for nondeterministic output).")
    parser.add_argument("--rows", type=int, default=150, help="Number of rows to generate for source/target tables.")
    parser.add_argument("--fail-rate", type=float, default=0.35, help="Fraction of rows to inject failures into (0-1).")
    parser.add_argument("--out-dir", type=str, default="random_data", help="Output base directory for generated files.")
    args = parser.parse_args()

    set_seed(args.seed)

    base_out = args.out_dir
    # Create directories
    os.makedirs(os.path.join(base_out, "source"), exist_ok=True)
    os.makedirs(os.path.join(base_out, "target"), exist_ok=True)

    print("Generating comprehensive test data...")

    # Show expected errors before generation
    NUM_ROWS = args.rows
    FAIL_RATE = args.fail_rate
    display_expected_errors(fail_rate=FAIL_RATE, num_rows=NUM_ROWS)

    # Generate main test data
    source_df = generate_source_data(num_rows=NUM_ROWS, fail_rate=0)
    target_df = generate_target_data(num_rows=NUM_ROWS, fail_rate=FAIL_RATE)

    # Save main tables
    source_df.to_csv(os.path.join(base_out, "source", "orders.csv"), index=False)
    target_df.to_csv(os.path.join(base_out, "target", "orders.csv"), index=False)
    print(f"✓ Generated {NUM_ROWS} rows of test data")
    print(f"  - Source: {len(source_df)} rows")
    print(f"  - Target: {len(target_df)} rows ({FAIL_RATE*100:.0f}% with random failures)")

    # Generate reference tables
    customers_df, warehouses_df = generate_reference_tables(num_rows=100)
    customers_df.to_csv(os.path.join(base_out, "source", "customers.csv"), index=False)
    customers_df.to_csv(os.path.join(base_out, "target", "customers.csv"), index=False)
    warehouses_df.to_csv(os.path.join(base_out, "source", "warehouses.csv"), index=False)
    warehouses_df.to_csv(os.path.join(base_out, "target", "warehouses.csv"), index=False)
    print("✓ Generated reference tables for relationship checks")

    # Generate comprehensive config
    config = generate_audit_config()
    config_path = os.path.join(base_out, "audit.yaml")
    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    print(f"✓ Generated config at {config_path}")

    # Print summary
    print("\nTest Data Summary:")
    print(f"  {len(source_df)} source rows × {len(source_df.columns)} columns")
    print(f"  {len(target_df)} target rows × {len(target_df.columns)} columns")
    print(f"\nChecks Exercised:")
    print("  ✓ Volume checks (row count comparisons)")
    print("  ✓ Identity checks (PK overlap)")
    print("  ✓ Aggregate checks (SUM, AVG, MIN, MAX, VARIANCE)")
    print("  ✓ Mapping checks (enum value mappings)")
    print("  ✓ Relationship checks (foreign keys to reference tables)")
    print("  ✓ Data constraint checks (NOT NULL, POSITIVE, etc.)")
    print("  ✓ String truncation checks")
    print("  ✓ Whitespace corruption checks")
    print("  ✓ Encoding corruption checks")
    print("  ✓ Enum equivalence checks")
    print("  ✓ Categorical distribution checks")
    print("  ✓ Datetime/TZ consistency checks")
    print("  ✓ Null/sentinel equivalence checks")
    print("  ✓ Numeric precision checks")
    print("  ✓ Boolean normalization checks")
    print("  ✓ Uniqueness checks")
    print(f"\nRun audit with: python run_audit.py --no-auth --headless")


if __name__ == "__main__":
    main()
