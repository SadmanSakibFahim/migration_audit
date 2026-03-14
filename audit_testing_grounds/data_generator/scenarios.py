import os
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

import pandas as pd

from .db_utils import create_sqlite_db
from .generators import (drop_column, generate_base_data,
                         generate_related_data, inject_data_corruption,
                         inject_special_chars, inject_volume_loss,
                         split_dataframe)


@dataclass
class Scenario:
    name: str
    description: str
    expected_result: Dict[str, str]  # e.g., {'verdict': 'GO'}
    generator_func: Callable[
        [str], None
    ]  # Function that writes source/target files to a path
    custom_config: Optional[Dict[str, Any]] = (
        None  # Custom table config to override defaults
    )


def create_perfect_match(output_dir: str):
    """Scenario: Source and Target are identical."""
    df = generate_base_data(100)
    os.makedirs(os.path.join(output_dir, "source"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "target"), exist_ok=True)
    df.to_csv(os.path.join(output_dir, "source", "users.csv"), index=False)
    df.to_csv(os.path.join(output_dir, "target", "users.csv"), index=False)


def create_volume_loss(output_dir: str):
    """Scenario: Target has significant missing rows."""
    src_df = generate_base_data(100)
    tgt_df = inject_volume_loss(src_df, loss_pct=0.10)  # 10% loss
    os.makedirs(os.path.join(output_dir, "source"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "target"), exist_ok=True)
    src_df.to_csv(os.path.join(output_dir, "source", "users.csv"), index=False)
    tgt_df.to_csv(os.path.join(output_dir, "target", "users.csv"), index=False)


def create_numeric_mismatch(output_dir: str):
    """Scenario: Data volume matches, but numeric values are corrupted."""
    src_df = generate_base_data(100)
    tgt_df = inject_data_corruption(
        src_df, "amount", corruption_pct=0.20, corruption_type="negative"
    )
    os.makedirs(os.path.join(output_dir, "source"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "target"), exist_ok=True)
    src_df.to_csv(os.path.join(output_dir, "source", "users.csv"), index=False)
    tgt_df.to_csv(os.path.join(output_dir, "target", "users.csv"), index=False)


# --- EDGE CASES ---
def create_empty_file(output_dir: str):
    src_df = generate_base_data(100)
    tgt_df = src_df.iloc[:0]
    os.makedirs(os.path.join(output_dir, "source"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "target"), exist_ok=True)
    src_df.to_csv(os.path.join(output_dir, "source", "users.csv"), index=False)
    tgt_df.to_csv(os.path.join(output_dir, "target", "users.csv"), index=False)


def create_null_values(output_dir: str):
    src_df = generate_base_data(100)
    tgt_df = inject_data_corruption(
        src_df, "amount", corruption_pct=0.1, corruption_type="null"
    )
    os.makedirs(os.path.join(output_dir, "source"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "target"), exist_ok=True)
    src_df.to_csv(os.path.join(output_dir, "source", "users.csv"), index=False)
    tgt_df.to_csv(os.path.join(output_dir, "target", "users.csv"), index=False)


def create_missing_column(output_dir: str):
    src_df = generate_base_data(100)
    tgt_df = drop_column(src_df, "amount")
    os.makedirs(os.path.join(output_dir, "source"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "target"), exist_ok=True)
    src_df.to_csv(os.path.join(output_dir, "source", "users.csv"), index=False)
    tgt_df.to_csv(os.path.join(output_dir, "target", "users.csv"), index=False)


def create_special_chars(output_dir: str):
    src_df = generate_base_data(100)
    tgt_df = inject_special_chars(src_df, "name", pct=0.2)
    os.makedirs(os.path.join(output_dir, "source"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "target"), exist_ok=True)
    src_df.to_csv(
        os.path.join(output_dir, "source", "users.csv"), index=False, encoding="utf-8"
    )
    tgt_df.to_csv(
        os.path.join(output_dir, "target", "users.csv"), index=False, encoding="utf-8"
    )


# --- COMPLEX & PERFORMANCE ---


def create_complex_n_to_1(output_dir: str):
    """Scenario: 3 source files merge into 1 target file."""
    full_df = generate_base_data(100)
    chunks = split_dataframe(full_df, num_chunks=3)
    os.makedirs(os.path.join(output_dir, "source"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "target"), exist_ok=True)
    for i, chunk in enumerate(chunks):
        chunk.to_csv(
            os.path.join(output_dir, "source", f"users_part_{i+1}.csv"), index=False
        )
    full_df.to_csv(os.path.join(output_dir, "target", "users.csv"), index=False)


def create_complex_1_to_n(output_dir: str):
    """Scenario: 1 source file splits into 2 target files."""
    full_df = generate_base_data(100)
    chunks = split_dataframe(full_df, num_chunks=2)
    os.makedirs(os.path.join(output_dir, "source"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "target"), exist_ok=True)
    full_df.to_csv(os.path.join(output_dir, "source", "users.csv"), index=False)
    chunks[0].to_csv(
        os.path.join(output_dir, "target", "users_part_1.csv"), index=False
    )
    chunks[1].to_csv(
        os.path.join(output_dir, "target", "users_part_2.csv"), index=False
    )


def create_complex_n_to_m(output_dir: str):
    """Scenario: 2 source files map to 2 target files (shuffling rows)."""
    full_df = generate_base_data(100)
    src_chunks = split_dataframe(full_df, num_chunks=2)
    tgt_chunk1 = full_df.iloc[:60]
    tgt_chunk2 = full_df.iloc[60:]
    os.makedirs(os.path.join(output_dir, "source"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "target"), exist_ok=True)
    src_chunks[0].to_csv(
        os.path.join(output_dir, "source", "users_src_1.csv"), index=False
    )
    src_chunks[1].to_csv(
        os.path.join(output_dir, "source", "users_src_2.csv"), index=False
    )
    tgt_chunk1.to_csv(
        os.path.join(output_dir, "target", "users_tgt_1.csv"), index=False
    )
    tgt_chunk2.to_csv(
        os.path.join(output_dir, "target", "users_tgt_2.csv"), index=False
    )


def create_complex_vertical_split(output_dir: str):
    """Scenario: 1 flat source file maps to 2 different target tables (Normalization)."""
    full_df = generate_base_data(100)[["id", "name", "amount", "category", "status"]]
    os.makedirs(os.path.join(output_dir, "source"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "target"), exist_ok=True)
    full_df.to_csv(os.path.join(output_dir, "source", "flat_data.csv"), index=False)
    tgt1 = full_df[["id", "name", "amount"]]
    tgt1.to_csv(os.path.join(output_dir, "target", "users.csv"), index=False)
    tgt2 = full_df[["id", "category", "status"]]
    tgt2.to_csv(os.path.join(output_dir, "target", "metadata.csv"), index=False)


def create_database_to_csv(output_dir: str):
    """
    Scenario: Source is a SQLite database, Target is a CSV file.
    This tests the SQLAlchemy integration.
    """
    df = generate_base_data(100)

    os.makedirs(os.path.join(output_dir, "source"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "target"), exist_ok=True)

    # 1. Create Source Database
    db_path = os.path.join(output_dir, "source", "audit.db")
    create_sqlite_db(db_path, "users", df)

    # 2. Create Target CSV
    df.to_csv(os.path.join(output_dir, "target", "users.csv"), index=False)


def create_zero_overlap(output_dir: str):
    """Scenario: Source and Target have same volume but 0% row overlap (different IDs)."""
    src_df = generate_base_data(100)
    tgt_df = generate_base_data(100)
    # Ensure IDs are disjoint
    tgt_df["id"] = range(101, 201)

    os.makedirs(os.path.join(output_dir, "source"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "target"), exist_ok=True)
    src_df.to_csv(os.path.join(output_dir, "source", "users.csv"), index=False)
    tgt_df.to_csv(os.path.join(output_dir, "target", "users.csv"), index=False)


def create_empty_source(output_dir: str):
    """Source is empty, Target has data."""
    os.makedirs(os.path.join(output_dir, "source"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "target"), exist_ok=True)
    # Empty CSV (header only)
    pd.DataFrame(columns=["id", "name", "amount"]).to_csv(
        os.path.join(output_dir, "source", "users.csv"), index=False
    )
    generate_base_data(20).to_csv(
        os.path.join(output_dir, "target", "users.csv"), index=False
    )


def create_missing_target(output_dir: str):
    """Source has data, Target doesn't exist."""
    os.makedirs(os.path.join(output_dir, "source"), exist_ok=True)
    generate_base_data(20).to_csv(
        os.path.join(output_dir, "source", "users.csv"), index=False
    )
    # Target directory exists but file is missing


def create_schema_mismatch(output_dir: str):
    """Target is missing a column (amount)."""
    src_df = generate_base_data(20)
    tgt_df = src_df.copy().drop(columns=["amount"])
    os.makedirs(os.path.join(output_dir, "source"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "target"), exist_ok=True)
    src_df.to_csv(os.path.join(output_dir, "source", "users.csv"), index=False)
    tgt_df.to_csv(os.path.join(output_dir, "target", "users.csv"), index=False)


def create_type_mismatch(output_dir: str):
    """Numeric column in Target contains non-numeric strings."""
    src_df = generate_base_data(20)
    tgt_df = src_df.copy()
    tgt_df["amount"] = tgt_df["amount"].astype(str)
    tgt_df.loc[0, "amount"] = "NOT_A_NUMBER"

    os.makedirs(os.path.join(output_dir, "source"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "target"), exist_ok=True)
    src_df.to_csv(os.path.join(output_dir, "source", "users.csv"), index=False)
    tgt_df.to_csv(os.path.join(output_dir, "target", "users.csv"), index=False)


def create_stress_test_chunked(output_dir: str):
    """Scenario: Large dataset (200k rows) for chunked processing test."""
    df = generate_base_data(200000)
    os.makedirs(os.path.join(output_dir, "source"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "target"), exist_ok=True)
    df.to_csv(os.path.join(output_dir, "source", "users.csv"), index=False)
    # Give target slightly different data if we want to test failures,
    # but for now let's test a perfect match in chunked mode.
    df.to_csv(os.path.join(output_dir, "target", "users.csv"), index=False)


def create_performance_test(output_dir: str):
    """Scenario: Large dataset (50k rows)."""
    df = generate_base_data(50000)
    os.makedirs(os.path.join(output_dir, "source"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "target"), exist_ok=True)
    df.to_csv(os.path.join(output_dir, "source", "users.csv"), index=False)
    df.to_csv(os.path.join(output_dir, "target", "users.csv"), index=False)


# --- MAPPINGS & RELATIONSHIPS ---


def create_mapping_violation(output_dir: str):
    """Scenario: Target has status values not in allowed list."""
    df = generate_base_data(100)
    tgt_df = df.copy()
    tgt_df.loc[0, "status"] = "BANNED"  # Not in ['Active', 'Inactive', 'Pending']
    os.makedirs(os.path.join(output_dir, "source"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "target"), exist_ok=True)
    df.to_csv(os.path.join(output_dir, "source", "users.csv"), index=False)
    tgt_df.to_csv(os.path.join(output_dir, "target", "users.csv"), index=False)


def create_relationship_violation(output_dir: str):
    """Scenario: Child table has orphans."""
    users_df = generate_base_data(50)
    orders_df = generate_related_data(users_df, 100)
    tgt_orders = orders_df.copy()
    tgt_orders.loc[0, "user_id"] = 9999  # Non-existent user
    os.makedirs(os.path.join(output_dir, "source"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "target"), exist_ok=True)
    users_df.to_csv(os.path.join(output_dir, "source", "users.csv"), index=False)
    users_df.to_csv(os.path.join(output_dir, "target", "users.csv"), index=False)
    orders_df.to_csv(os.path.join(output_dir, "source", "orders.csv"), index=False)
    tgt_orders.to_csv(os.path.join(output_dir, "target", "orders.csv"), index=False)


SCENARIOS = {
    "perfect_match": Scenario(
        name="Perfect Match",
        description="Source and target are identical. Should PASS all checks.",
        expected_result={"verdict": "GO"},
        generator_func=create_perfect_match,
    ),
    "volume_loss": Scenario(
        name="Volume Loss",
        description="Target missing 10% rows. Should FAIL volume checks.",
        expected_result={"verdict": "NO-GO"},
        generator_func=create_volume_loss,
    ),
    "numeric_mismatch": Scenario(
        name="Numeric Mismatch",
        description="Amounts differ in target. Should FAIL aggregate checks.",
        expected_result={"verdict": "NO-GO"},
        generator_func=create_numeric_mismatch,
    ),
    "empty_target": Scenario(
        name="Empty Target File",
        description="Target file has 0 rows. Should FAIL volume checks.",
        expected_result={"verdict": "NO-GO"},
        generator_func=create_empty_file,
    ),
    "null_values": Scenario(
        name="Null Values",
        description="Nulls in aggregate columns. Should FAIL.",
        expected_result={"verdict": "NO-GO"},
        generator_func=create_null_values,
    ),
    "missing_column": Scenario(
        name="Missing Column",
        description="Target missing 'amount' column. Should FAIL (Strict Schema).",
        expected_result={"verdict": "NO-GO"},  # Updated for strict schema validation
        generator_func=create_missing_column,
    ),
    "special_chars": Scenario(
        name="Special Characters",
        description="Unicode chars. Should PASS.",
        expected_result={"verdict": "GO"},
        generator_func=create_special_chars,
    ),
    "complex_n_to_1": Scenario(
        name="Complex N:1 (Merge)",
        description="3 source files merge into 1 target. Should PASS.",
        expected_result={"verdict": "GO"},
        generator_func=create_complex_n_to_1,
        custom_config={
            "complex_mapping": {
                "mapping_type": "N:1",
                "aggregation_strategy": "merge",
                "sources": [
                    {"path": "source/users_part_1.csv"},
                    {"path": "source/users_part_2.csv"},
                    {"path": "source/users_part_3.csv"},
                ],
                "targets": [{"path": "target/users.csv", "primary_key": "id"}],
            },
            "primary_key": "id",
            "aggregates": ["amount"],
        },
    ),
    "complex_1_to_n": Scenario(
        name="Complex 1:N (Split)",
        description="1 source file splits into 2 targets. Should PASS.",
        expected_result={"verdict": "GO"},
        generator_func=create_complex_1_to_n,
        custom_config={
            "complex_mapping": {
                "mapping_type": "1:N",
                "split_strategy": "distribute",
                "sources": [{"path": "source/users.csv"}],
                "targets": [
                    {"path": "target/users_part_1.csv", "primary_key": "id"},
                    {"path": "target/users_part_2.csv", "primary_key": "id"},
                ],
            },
            "primary_key": "id",
            "aggregates": ["amount"],
        },
    ),
    "complex_n_to_m": Scenario(
        name="Complex N:M (Many-to-Many)",
        description="2 sources mapped to 2 targets (re-sharded). Should PASS.",
        expected_result={"verdict": "GO"},
        generator_func=create_complex_n_to_m,
        custom_config={
            "complex_mapping": {
                "mapping_type": "N:M",
                "aggregation_strategy": "merge",
                "sources": [
                    {"path": "source/users_src_1.csv"},
                    {"path": "source/users_src_2.csv"},
                ],
                "targets": [
                    {"path": "target/users_tgt_1.csv", "primary_key": "id"},
                    {"path": "target/users_tgt_2.csv", "primary_key": "id"},
                ],
            },
            "primary_key": "id",
            "aggregates": ["amount"],
        },
    ),
    "complex_vertical_split": Scenario(
        name="Complex 1:N (Vertical Split / Normalization)",
        description="1 flat file split into 2 tables with different schemas. Reconstructed using 'join' strategy.",
        expected_result={"verdict": "GO"},
        generator_func=create_complex_vertical_split,
        custom_config={
            "complex_mapping": {
                "mapping_type": "1:N",
                "split_strategy": "join",
                "sources": [{"path": "source/flat_data.csv"}],
                "targets": [
                    {"path": "target/users.csv", "primary_key": "id"},
                    {"path": "target/metadata.csv", "primary_key": "id"},
                ],
            },
            "primary_key": "id",
            "aggregates": ["amount"],
        },
    ),
    "performance_large": Scenario(
        name="Performance (50k rows)",
        description="50,000 rows. Should PASS and finish quickly.",
        expected_result={"verdict": "GO"},
        generator_func=create_performance_test,
    ),
    "mapping_violation": Scenario(
        name="Mapping Violation",
        description="Value constraint violation in target. Should FAIL.",
        expected_result={"verdict": "NO-GO"},
        generator_func=create_mapping_violation,
        custom_config={
            "source": "source/users.csv",
            "target": "target/users.csv",
            "primary_key": "id",
            "mappings": [
                {
                    "columns": ["status"],
                    "allowed_values": ["Active", "Inactive", "Pending"],
                }
            ],
        },
    ),
    "relationship_violation": Scenario(
        name="Relationship Violation",
        description="Orphan records in child table. Should FAIL.",
        expected_result={"verdict": "NO-GO"},
        generator_func=create_relationship_violation,
        custom_config={
            "users": {
                "source": "source/users.csv",
                "target": "target/users.csv",
                "primary_key": "id",
            },
            "orders": {
                "source": "source/orders.csv",
                "target": "target/orders.csv",
                "primary_key": "id",
                "relationships": [
                    {
                        "child": {
                            "target": "target/orders.csv",
                            "fk_column": "user_id",
                        },
                        "parent": {"target": "target/users.csv", "pk_column": "id"},
                    }
                ],
            },
        },
    ),
    "database_to_csv": Scenario(
        name="Database to CSV",
        description="Source is SQLite, Target is CSV. Should PASS.",
        expected_result={"verdict": "GO"},
        generator_func=create_database_to_csv,
        custom_config={
            "source": "sqlite:///source/audit.db/users",
            "target": "target/users.csv",
            "primary_key": "id",
            "aggregates": ["amount"],
        },
    ),
    "stress_test_chunked": Scenario(
        name="Stress Test (200k Rows, Chunked)",
        description="Audits 200,000 rows in 50,000 row chunks. Should PASS.",
        expected_result={"verdict": "GO"},
        generator_func=create_stress_test_chunked,
        custom_config={
            "source": "source/users.csv",
            "target": "target/users.csv",
            "primary_key": "id",
            "aggregates": ["amount"],
            "chunk_size": 50000,
        },
    ),
    "zero_overlap": Scenario(
        name="Zero Overlap (Identity Mismatch)",
        description="Source and Target have 0 common Primary Keys. Should FAIL.",
        expected_result={"verdict": "NO-GO"},
        generator_func=create_zero_overlap,
        custom_config={
            "source": "source/users.csv",
            "target": "target/users.csv",
            "primary_key": "id",
            "aggregates": ["amount"],
            "chunk_size": 20,
        },
    ),
    "empty_source": Scenario(
        name="Empty Source File",
        description="Source is empty, Target has rows. Should fail volume check.",
        expected_result={"verdict": "NO-GO"},
        generator_func=create_empty_source,
        custom_config={
            "source": "source/users.csv",
            "target": "target/users.csv",
            "primary_key": "id",
            "aggregates": ["amount"],
        },
    ),
    "missing_target": Scenario(
        name="Missing Target File",
        description="Target file is missing from disk. Should fail loading.",
        expected_result={"verdict": "ERROR"},  # New exit status or verdict
        generator_func=create_missing_target,
        custom_config={
            "source": "source/users.csv",
            "target": "target/users.csv",
            "primary_key": "id",
        },
    ),
    "schema_mismatch": Scenario(
        name="Schema Mismatch",
        description="Target is missing the 'amount' column. Should FAIL schema check.",
        expected_result={"verdict": "NO-GO"},
        generator_func=create_schema_mismatch,
        custom_config={
            "source": "source/users.csv",
            "target": "target/users.csv",
            "primary_key": "id",
            "aggregates": ["amount"],
        },
    ),
    "type_mismatch": Scenario(
        name="Type Mismatch",
        description="Numeric column 'amount' contains junk strings. Should WARN/FAIL.",
        expected_result={"verdict": "NO-GO"},
        generator_func=create_type_mismatch,
        custom_config={
            "source": "source/users.csv",
            "target": "target/users.csv",
            "primary_key": "id",
            "aggregates": ["amount"],
        },
    ),
}
