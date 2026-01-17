from pydantic import BaseModel, Field
from typing import List, Dict, Optional

class ToleranceConfig(BaseModel):
    volume_loss_pct: float = 0.1
    aggregate_pct_diff: float = 1.0

class MappingConfig(BaseModel):
    columns: List[str]
    allowed_values: List[str]

class RelationshipConfig(BaseModel):
    child: Dict[str, str]  # keys: "target", "fk_column"
    parent: Dict[str, str] # keys: "target", "pk_column"

class TableConfig(BaseModel):
    source: str
    target: str
    primary_key: str
    aggregates: List[str] = Field(default_factory=list)
    mappings: List[MappingConfig] = Field(default_factory=list)
    relationships: List[RelationshipConfig] = Field(default_factory=list)
    data_constraints: Dict[str, List[str]] = Field(default_factory=dict)

class AuditConfig(BaseModel):
    tables: Dict[str, TableConfig]
    tolerances: ToleranceConfig = Field(default_factory=ToleranceConfig)
