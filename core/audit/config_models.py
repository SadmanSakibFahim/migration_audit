from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field


class ToleranceConfig(BaseModel):
    volume_loss_pct: float = 0.1
    aggregate_pct_diff: float = 1.0


class MappingConfig(BaseModel):
    columns: List[str]
    allowed_values: List[str]


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

