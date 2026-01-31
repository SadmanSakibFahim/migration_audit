from core.loader import load_table
from core.result import TestResult
from core.enums import CheckStatus
import pandas as pd
import random
from typing import List, Dict, Any, Optional

class IncrementalRunner:
    """
    Runner designed for large-scale data auditing using chunked processing.
    Maintains state (counts, sums) across iterations to avoid OOM.
    """
    def __init__(
        self,
        table_name: str,
        meta: Any,
        volume_tolerance: float = 0.1,
        aggregate_tolerance: float = 1.0,
        chunk_size: int = 50000
    ):
        self.table_name = table_name
        self.meta = meta
        self.volume_tolerance = volume_tolerance
        self.aggregate_tolerance = aggregate_tolerance
        self.chunk_size = chunk_size
        self.results = []
        
        # State Accumulators
        self.src_row_count = 0
        self.tgt_row_count = 0
        self.src_aggregates = {} # {col: running_sum}
        self.tgt_aggregates = {} # {col: running_sum}
        self.mapping_errors = [] # Collected during target sweep
        self.constraint_errors = [] # Collected during target sweep
        self.junk_counts = {} # {col: count}

        
        # Identity Sampling (Reservoir Sampling)
        self.sample_size = 1000
        self.src_pk_sample = []
        self.src_pk_total_processed = 0
        self.tgt_pk_matched_count = 0
        self.tgt_pks_seen = set() # Only used if target fits in memory, but we stream it.
        # For true streaming, we'll mark which sampled IDs were found in the target.
        self.sampled_ids_found = {} # {id: found_bool}

    def process_source(self, path: str):
        """Iterate through source path in chunks and accumulate metrics."""
        chunks = load_table(path, chunk_size=self.chunk_size)
        
        # Initialize aggregate tracking
        aggregates = getattr(self.meta, "aggregates", [])
        for col in aggregates:
            self.src_aggregates[col] = 0.0

        for chunk in chunks:
            self.src_row_count += len(chunk)
            
            # Identity Sampling (Reservoir Sampling)
            pk = getattr(self.meta, "primary_key", None)
            if pk and pk in chunk.columns:
                for val in chunk[pk].dropna().tolist():
                    self.src_pk_total_processed += 1
                    if len(self.src_pk_sample) < self.sample_size:
                        self.src_pk_sample.append(val)
                    else:
                        # Randomly replace existing sample
                        r = random.randint(0, self.src_pk_total_processed - 1)
                        if r < self.sample_size:
                            self.src_pk_sample[r] = val
            
            for col in aggregates:
                if col in chunk.columns:
                    self.src_aggregates[col] += pd.to_numeric(chunk[col], errors='coerce').sum()

    def process_target(self, path: str):
        """Iterate through target path in chunks, accumulate metrics and run row-level checks."""
        from checks.data_constraints import check_data_constraints
        from core.check_registry import CHECK_REGISTRY

        # Reset found map
        self.sampled_ids_found = {id_val: False for id_val in self.src_pk_sample}
        pk = getattr(self.meta, "primary_key", None)

        chunks = load_table(path, chunk_size=self.chunk_size)
        
        aggregates = getattr(self.meta, "aggregates", [])
        for col in aggregates:
            self.tgt_aggregates[col] = 0.0

        for chunk in chunks:
            self.tgt_row_count += len(chunk)
            
            # Identity Check: Do any of our sampled Source IDs exist in this Target chunk?
            if pk and pk in chunk.columns:
                chunk_ids = set(chunk[pk].dropna().tolist())
                for sampled_id in self.src_pk_sample:
                    if sampled_id in chunk_ids:
                        self.sampled_ids_found[sampled_id] = True
            
            # Aggregate accumulation
            for col in aggregates:
                if col in chunk.columns:
                    # Junk detection: count non-numeric values that aren't NaN
                    vals_coerced = pd.to_numeric(chunk[col], errors='coerce')
                    junk_count = chunk[col].notna().sum() - vals_coerced.notna().sum()
                    if col not in self.junk_counts:
                        self.junk_counts[col] = 0
                    self.junk_counts[col] += int(junk_count)

                    self.tgt_aggregates[col] += vals_coerced.sum()
            
            # Mapping Checks (Value validation)
            for mapping in getattr(self.meta, "mappings", []):
                for fn in CHECK_REGISTRY.get("mappings", []):
                    res = fn(chunk, mapping.columns, mapping.allowed_values, self.table_name)
                    if res.status == CheckStatus.FAIL:
                        self.mapping_errors.append(res.message)

            # Data Constraint Checks
            for col, constraints in getattr(self.meta, "data_constraints", {}).items():
                if isinstance(constraints, str):
                    constraints = [constraints]
                res = check_data_constraints(chunk, {col: constraints}, self.table_name)
                if res.status == CheckStatus.FAIL:
                    self.constraint_errors.append(res.message)

    def finalize(self) -> List[TestResult]:
        """Compare accumulated states and generate final TestResults."""
        
        # 1. Volume Check
        diff = abs(self.src_row_count - self.tgt_row_count)
        loss_pct = (diff / self.src_row_count * 100) if self.src_row_count > 0 else 0
        
        status = CheckStatus.PASS if loss_pct <= self.volume_tolerance else CheckStatus.FAIL
        self.results.append(TestResult(
            name=f"Incremental Volume Check: {self.table_name}",
            status=status,
            message=f"Rows: Source={self.src_row_count}, Target={self.tgt_row_count}. Loss={loss_pct:.2f}%",
            details={"src_rows": self.src_row_count, "tgt_rows": self.tgt_row_count}
        ))

        # 2. Aggregate Checks
        for col in self.src_aggregates:
            src_val = self.src_aggregates[col]
            tgt_val = self.tgt_aggregates.get(col, 0.0)
            
            diff = abs(src_val - tgt_val)
            diff_pct = (diff / src_val * 100) if src_val != 0 else (100 if tgt_val != 0 else 0)
            
            status = CheckStatus.PASS if diff_pct <= self.aggregate_tolerance else CheckStatus.FAIL
            self.results.append(TestResult(
                name=f"Incremental Aggregate Check: {self.table_name} - {col}",
                status=status,
                message=f"Sum for {col}: Source={src_val}, Target={tgt_val}. Diff={diff_pct:.2f}%"
            ))

        # 3. Identity Check (Probabilistic based on Sample)
        pk = getattr(self.meta, "primary_key", None)
        if pk and self.src_pk_sample:
            found_count = sum(1 for v in self.sampled_ids_found.values() if v)
            overlap_pct = (found_count / len(self.src_pk_sample) * 100) if self.src_pk_sample else 0
            
            status = CheckStatus.PASS if overlap_pct >= 95 else (CheckStatus.WARN if overlap_pct > 0 else CheckStatus.FAIL)
            message = f"Incremental Identity Check: Found ~{overlap_pct:.1f}% of sampled source IDs in target."
            if overlap_pct == 0:
                message = "CRITICAL: 0% overlap detected among sampled IDs!"
                
            self.results.append(TestResult(
                name=f"Incremental Identity Check: {self.table_name}",
                status=status,
                message=message,
                details={"sample_size": len(self.src_pk_sample), "found_in_target": found_count}
            ))

        # 4. Data Quality (Junk)
        for col, count in self.junk_counts.items():
            if count > 0:
                self.results.append(TestResult(
                    name=f"Incremental Data Quality: {self.table_name}.{col}",
                    status=CheckStatus.FAIL,
                    message=f"Found {count} non-numeric values in numeric column '{col}' during streaming audit.",
                    details={"junk_count": count}
                ))

        # 5. Mapping Errors (Summary)
        if self.mapping_errors:
            self.results.append(TestResult(
                name=f"Incremental Mapping Checks: {self.table_name}",
                status=CheckStatus.FAIL,
                message=f"Found {len(self.mapping_errors)} chunk-level mapping violations.",
                details={"errors": list(set(self.mapping_errors))[:10]} # Unique samples
            ))

        # 4. Constraint Errors (Summary)
        if self.constraint_errors:
            self.results.append(TestResult(
                name=f"Incremental Constraint Checks: {self.table_name}",
                status=CheckStatus.FAIL,
                message=f"Found {len(self.constraint_errors)} chunk-level constraint violations.",
                details={"errors": list(set(self.constraint_errors))[:10]}
            ))

        return self.results
