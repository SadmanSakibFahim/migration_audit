# Complex Data Mapping Analysis

## Question
Can the codebase conduct audits when:
1. **One source table branches into multiple target tables** (1:N mapping)
2. **Multiple source tables merge into one target table** (N:1 mapping)

## Answer

### ❌ **NOT CURRENTLY SUPPORTED**

The current codebase architecture is **fundamentally 1:1 table-centric** and cannot handle complex N:1 or 1:N data mappings.

---

## Current Architecture Limitations

### 1. **Table Configuration Model (Rigid 1:1 Structure)**

**File:** `core/config_models.py`

```python
class TableConfig(BaseModel):
    source: str          # ← ONE source file
    target: str          # ← ONE target file
    primary_key: str
    aggregates: List[str]
    mappings: List[MappingConfig]
    relationships: List[RelationshipConfig]
    data_constraints: Dict[str, List[str]]
```

**Issue:** Each table config has exactly one `source` and one `target` string. There is no support for:
- Multiple source files for a single table
- Multiple target files for a single source
- Source/target arrays or nested structures

### 2. **Data Loading (1:1 File Mapping)**

**File:** `core/loader.py` / `run_audit.py`

```python
src_df = load_table_safe(meta.source, table_name)  # Single file
tgt_df = load_table_safe(meta.target, table_name)  # Single file
```

**Issue:** Loads exactly one source dataframe and one target dataframe per table. No support for:
- Loading and combining multiple files
- Splitting data across multiple files

### 3. **Volume Check (Single Table Count Comparison)**

**File:** `checks/volume.py`

```python
def check_volume(name: str, src_df: pd.DataFrame, tgt_df: pd.DataFrame, tolerance_pct: float = 0.0) -> TestResult:
    src_count = len(src_df)
    tgt_count = len(tgt_df)
```

**Issue:** Compares simple row counts between two dataframes. For branching scenarios:
- Cannot handle: "Source table A has 1000 rows split across target tables B (600 rows) and C (400 rows)"
- Naive 1:1 count comparison would fail (1000 ≠ 600)

### 4. **Aggregate Checks (Same Limitation)**

**File:** `checks/aggregates.py`

```python
def check_sum(src_df: pd.DataFrame, tgt_df: pd.DataFrame, column: str, name: str, tolerance: float) -> TestResult:
    src_sum = src_df[column].dropna().sum()
    tgt_sum = tgt_df[column].dropna().sum()
```

**Issue:** Compares single source aggregate to single target aggregate. Cannot:
- Sum across multiple target tables and compare to one source
- Split a source aggregate across multiple target tables

### 5. **Relationship Checks (Binary Child-Parent Only)**

**File:** `checks/relationships.py` / `core/check_runner.py`

```python
class RelationshipConfig(BaseModel):
    child: Dict[str, str]   # Exactly ONE child table
    parent: Dict[str, str]  # Exactly ONE parent table
```

**Issue:** Relationships are hard-wired as binary child-parent pairs. For complex branching:
- Cannot express: "Source user table links to both target tables orders_live and orders_archive"
- No support for multi-hop or star-schema relationships

### 6. **Main Audit Loop (Table-by-Table Processing)**

**File:** `run_audit.py`

```python
for table_name in tqdm(tables_list, desc="Auditing tables"):
    meta = tables_cfg[table_name]
    src_df = load_table_safe(meta.source, table_name)
    tgt_df = load_table_safe(meta.target, table_name)
    runner = CheckRunner(table_name=table_name, meta=meta, src_df=src_df, tgt_df=tgt_df, ...)
```

**Issue:** Loop processes exactly one source → one target per iteration. Cannot:
- Orchestrate multi-file aggregation
- Handle table dependencies beyond simple foreign keys
- Manage cross-table lineage tracking

---

## Scenarios That WILL FAIL

### Scenario 1: Source Branching to Multiple Targets

**Migration Pattern:**
```
Source: users.csv (1000 rows)
        ↓
        ├─→ Target: users_active.csv (700 rows) [status = 'active']
        └─→ Target: users_inactive.csv (300 rows) [status = 'inactive']
```

**Why it fails:**
- Volume check compares: 1000 (source) vs 700 (target) → **FAIL** (even though combined 700+300=1000)
- Aggregate checks compare individual sums instead of combined
- No lineage tracking to know data was intentionally split

---

### Scenario 2: Multiple Sources Merging to One Target

**Migration Pattern:**
```
Source: orders_2023.csv (500 rows) ──┐
Source: orders_2024.csv (600 rows) ──┤─→ Target: orders_consolidated.csv (1100 rows)
Source: orders_2025.csv (200 rows) ──┘
```

**Why it fails:**
- Data loader only reads one source file per table
- No aggregation logic to combine source dataframes
- Volume check would try to compare first source (500) vs target (1100) → **FAIL**
- No way to express "this target came from 3 sources"

---

### Scenario 3: Cross-Table Joins During Migration

**Migration Pattern:**
```
Source: users.csv ──┐
                    └─→ Joined & split → Target: user_profiles.csv
Source: profiles.csv ┘                    Target: user_preferences.csv
```

**Why it fails:**
- No join orchestration in the framework
- Each table config is independent—no cross-table logic
- Relationships only work for FK validation, not for expressing join lineage

---

## What CURRENTLY WORKS (1:1 Scenarios)

✅ **Simple 1:1 Table Mappings:**
- One source CSV → One target CSV
- Direct column mappings
- FK relationships between pairs of tables
- Basic volume, aggregate, and constraint validation

✅ **Supported Relationship Types:**
- Parent-child foreign key validation (orphan detection)
- Single-level referential integrity

---

## Required Changes to Support N:1 and 1:N Mappings

To extend the framework, the following architectural changes would be needed:

### 1. **Update Configuration Model**

```python
class SourceMapping(BaseModel):
    files: Union[str, List[str]]  # Single or multiple files
    combine_method: Optional[str]  # "union", "concat", etc.
    combine_keys: Optional[List[str]]  # Keys for combining

class TargetMapping(BaseModel):
    files: Union[str, List[str]]  # Single or multiple files
    split_method: Optional[str]  # How data is split
    split_key: Optional[str]  # Column used for splitting

class TableConfig(BaseModel):
    sources: SourceMapping  # Was: source (single)
    targets: TargetMapping  # Was: target (single)
    lineage: Optional[Dict]  # Track multi-table flows
```

### 2. **Add Data Orchestration Layer**

```python
class DataOrchestrator:
    def load_sources(self, source_mapping) -> pd.DataFrame:
        """Load and combine multiple source files"""
        dfs = [load_table(f) for f in source_mapping.files]
        return pd.concat(dfs)  # or other join logic
    
    def load_targets(self, target_mapping) -> Dict[str, pd.DataFrame]:
        """Load multiple target files"""
        return {f: load_table(f) for f in target_mapping.files}
```

### 3. **Enhance Validation Checks**

```python
def check_volume_distributed(
    source_df: pd.DataFrame,
    target_dfs: Dict[str, pd.DataFrame],  # Multiple targets
    tolerance_pct: float
) -> TestResult:
    """Compare source rows to sum of target rows"""
    src_count = len(source_df)
    tgt_total = sum(len(df) for df in target_dfs.values())
    # Now 1000 source + 700 target + 300 target = success
```

### 4. **Add Lineage & Mapping Metadata**

```python
class DataLineage(BaseModel):
    source_file: str
    target_files: List[str]
    mapping_rules: Dict  # How source rows map to targets
    split_condition: Optional[str]  # e.g., "WHERE status = 'active'"
```

### 5. **Redesign Audit Loop**

```python
# Current: for each table → run checks
# New: for each logical mapping unit → run checks across all source/target combinations
```

---

## Workaround (Current Limitation)

### Option 1: Pre-Process Data Before Audit
Create intermediate CSV files that align 1:1 before running the audit:
- Combine multiple sources into one staging CSV
- Split one source into multiple intermediate CSVs
- Then audit the aligned files

### Option 2: Manual Lineage Tracking
Document the N:1 or 1:N mapping separately and:
1. Run audits on individual 1:1 pairs
2. Manually validate cross-table consistency
3. Use `debug_data.py` to inspect intermediate states

### Option 3: Fork for Custom Implementation
Extend the framework with a new module `checks/complex_mappings.py` that:
- Accepts configuration with multiple sources/targets
- Implements custom validation logic
- Integrates with existing check registry

---

## Summary Table

| Capability | Supported | Notes |
|-----------|-----------|-------|
| 1:1 Table Mapping | ✅ Yes | Core architecture |
| 1:N Branching | ❌ No | Would need multi-target support |
| N:1 Merging | ❌ No | Would need multi-source aggregation |
| N:N Complex Joins | ❌ No | Would need orchestration layer |
| FK Relationships | ✅ Yes | Binary pairs only |
| Cross-Table Lineage | ❌ No | Not tracked |
| Data Combination Logic | ❌ No | No join/union orchestration |
| Distributed Validation | ❌ No | Only supports single source/target per check |

---

## Recommendation

**For immediate use:** Use the framework for 1:1 mappings. Pre-process complex mappings into aligned 1:1 CSV pairs before running the audit.

**For future enhancement:** Implement the architectural changes outlined above to support N:1 and 1:N scenarios. This would require significant refactoring of the data loading, check execution, and result aggregation logic.