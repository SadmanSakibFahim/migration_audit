from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class ToleranceConfig(BaseModel):
    volume_loss_pct: float = 0.1
    aggregate_pct_diff: float = 1.0


class MappingConfig(BaseModel):
    columns: List[str]
    allowed_values: List[str]


# ── Reddit Feedback: new check config models ──────────────────────────────────

class StringColumnConfig(BaseModel):
    """Config for string validation checks on a single column."""
    column: str
    max_length: Optional[int] = Field(
        default=None,
        description="Declared max character length (e.g. 255 for VARCHAR(255)). "
                    "If omitted, inferred from max observed length in target.",
    )
    check_whitespace: bool = Field(
        default=False,
        description="If True, checks for whitespace corruption/normalization via strip()."
    )
    check_encoding: bool = Field(
        default=False,
        description="If True, checks for encoding mojibake or unicode replacement chars."
    )


class EnumColumnConfig(BaseModel):
    """Config for an enum equivalence check on a single column."""
    column: str
    mapping: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional source_value -> target_value mapping. "
                    "If omitted, raw distinct value sets are compared.",
    )
    check_distribution: bool = Field(
        default=False,
        description="If True, compares the categorical distribution of values."
    )
    distribution_tolerance_pct: float = Field(
        default=0.05,
        description="Max allowed shift in category distribution percentage (e.g. 0.05 for 5%)."
    )


class DatetimeColumnConfig(BaseModel):
    """Config for a timezone/DST consistency check on a single datetime column."""
    column: str
    expected_tz: Optional[str] = Field(
        default=None,
        description="Expected timezone string (e.g. 'UTC'). If set, flags non-matching TZ.",
    )


class NullSentinelConfig(BaseModel):
    """Config for a null/sentinel equivalence check on a single column."""
    column: str
    sentinels: List[Any] = Field(
        description="List of values to treat as null equivalents, e.g. [0, -1, 'N/A', ''].",
    )


# ── Phase 2: Advanced Constraint Config Models ────────────────────────────────

class NumericColumnConfig(BaseModel):
    """Config for numeric precision/scale checks."""
    column: str
    expected_precision: Optional[int] = Field(
        default=None,
        description="Total number of digits allowed."
    )
    expected_scale: Optional[int] = Field(
        default=None,
        description="Number of digits allowed after the decimal point."
    )

class BooleanColumnConfig(BaseModel):
    """Config for boolean normalization checks."""
    column: str
    true_values: List[str] = Field(
        default_factory=lambda: ["Y", "1", "True", "true", "T", "t", "yes", "Yes"],
        description="List of string values to treat as True."
    )
    false_values: List[str] = Field(
        default_factory=lambda: ["N", "0", "False", "false", "F", "f", "no", "No"],
        description="List of string values to treat as False."
    )

# ─────────────────────────────────────────────────────────────────────────────


class RelationshipConfig(BaseModel):
    child: Dict[str, str]  # keys: "target", "fk_column"
    parent: Dict[str, str]  # keys: "target", "pk_column"


# New: Support for complex table mappings
class SourceTableConfig(BaseModel):
    """Configuration for a single source table in a mapping."""

    path: str
    primary_key: Optional[str] = None  # Optional if not needed for this source
    column_mapping: Optional[Dict[str, str]] = (
        None  # Maps source column -> target column
    )
    query: Optional[str] = None  # Custom SQL query (overrides table name in path)


class TargetTableConfig(BaseModel):
    """Configuration for a single target table in a mapping."""

    path: str
    primary_key: str
    column_mapping: Optional[Dict[str, str]] = (
        None  # Maps source column -> target column
    )
    query: Optional[str] = None  # Custom SQL query (overrides table name in path)


class ComplexMappingConfig(BaseModel):
    """Configuration for complex mappings (N:1, 1:N, N:M)."""

    sources: List[SourceTableConfig]  # Multiple source tables (N:1 or N:M)
    targets: List[TargetTableConfig]  # Multiple target tables (1:N or N:M)
    mapping_type: str = Field(
        default="1:1", description="Type: '1:1', '1:N', 'N:1', 'N:M'"
    )
    aggregation_strategy: Optional[str] = Field(
        default=None,
        description="For N:1 mappings: 'sum', 'count', 'merge', 'first', 'last'",
    )
    split_strategy: Optional[str] = Field(
        default=None, description="For 1:N mappings: 'copy', 'distribute', 'filter'"
    )


class TableConfig(BaseModel):
    # Support both simple (backward compatible) and complex mappings
    source: Optional[Union[str, List[SourceTableConfig]]] = None
    target: Optional[Union[str, List[TargetTableConfig]]] = None
    # Complex mapping configuration (takes precedence if provided)
    complex_mapping: Optional[ComplexMappingConfig] = None
    
    # Simple column mapping for 1:1 table relationships
    column_mapping: Optional[Dict[str, str]] = Field(
        default_factory=dict,
        description="Maps source column names to target column names for simple mappings."
    )

    # Custom SQL queries for simple mappings
    source_query: Optional[str] = None
    target_query: Optional[str] = None

    primary_key: str
    aggregates: List[str] = Field(default_factory=list)
    # Support column-level aggregate mappings for complex scenarios
    aggregate_column_mapping: Optional[Dict[str, str]] = Field(
        default=None,
        description="Maps target column names to source column names for aggregates",
    )
    mappings: List[MappingConfig] = Field(default_factory=list)
    relationships: List[RelationshipConfig] = Field(default_factory=list)
    data_constraints: Dict[str, List[str]] = Field(default_factory=dict)

    # Reddit Feedback: new check configurations
    string_columns: List[StringColumnConfig] = Field(
        default_factory=list,
        description="Columns to check for silent string truncation.",
    )
    enum_columns: List[EnumColumnConfig] = Field(
        default_factory=list,
        description="Columns to check for enum value equivalence.",
    )
    datetime_columns: List[DatetimeColumnConfig] = Field(
        default_factory=list,
        description="Columns to check for timezone/DST consistency.",
    )
    null_sentinels: List[NullSentinelConfig] = Field(
        default_factory=list,
        description="Columns with declared sentinel values to normalise before null-rate comparison.",
    )

    # Phase 2: Advanced Constraint Checks
    numeric_precision_columns: List[NumericColumnConfig] = Field(
        default_factory=list,
        description="Columns to check for numeric precision and scale drift."
    )
    boolean_columns: List[BooleanColumnConfig] = Field(
        default_factory=list,
        description="Columns to check for boolean normalisation."
    )
    unique_columns: List[str] = Field(
        default_factory=list,
        description="List of columns that should maintain uniqueness/cardinality during migration."
    )

    def is_complex_mapping(self) -> bool:
        """Check if this table uses complex mapping configuration."""
        return self.complex_mapping is not None

    def get_source_paths(self) -> List[str]:
        """Get all source paths for this table configuration."""
        if self.complex_mapping:
            return [src.path for src in self.complex_mapping.sources]
        elif isinstance(self.source, list):
            return [src.path for src in self.source]
        elif isinstance(self.source, str):
            return [self.source]
        return []

    def get_target_paths(self) -> List[str]:
        """Get all target paths for this table configuration."""
        if self.complex_mapping:
            return [tgt.path for tgt in self.complex_mapping.targets]
        elif isinstance(self.target, list):
            return [tgt.path for tgt in self.target]
        elif isinstance(self.target, str):
            return [self.target]
        return []


class AuditConfig(BaseModel):
    tables: Dict[str, TableConfig]
    tolerances: ToleranceConfig = Field(default_factory=ToleranceConfig)
    chunk_size: Optional[int] = Field(
        default=None,
        description="If set, enables incremental (chunked) processing for large files.",
    )
    large_file_threshold_mb: float = Field(
        default=50.0,
        description="Threshold (MB) to auto-trigger incremental processing for compatible tables.",
    )
    strict_schema: bool = Field(
        default=False,
        description="If set, unexpected columns in target cause a FAIL.",
    )

