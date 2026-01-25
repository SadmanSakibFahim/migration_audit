class CheckRunner:
    def __init__(
        self,
        table_name,
        meta,
        src_df,
        tgt_df,
        volume_tolerance=0.1,
        aggregate_tolerance=1.0,
    ):
        self.table_name = table_name
        self.meta = meta
        self.src_df = src_df
        self.tgt_df = tgt_df
        self.volume_tolerance = volume_tolerance
        self.aggregate_tolerance = aggregate_tolerance
        self.results = []
        self.is_complex = meta.is_complex_mapping() if hasattr(meta, 'is_complex_mapping') else False

    def _normalize_result(self, result):
        """Ensure all check outputs become List[TestResult]."""
        if result is None:
            return []
        if isinstance(result, list):
            return result
        return [result]

    def execute_all(self):
        """Run all configured checks and return normalized List[TestResult]."""
        from core.check_registry import CHECK_REGISTRY
        from core.loader import load_table
        from checks.data_constraints import check_data_constraints

        # -----------------------------
        # Volume checks
        # -----------------------------
        mapping_type = None
        expected_ratio = None
        if self.is_complex and hasattr(self.meta, 'complex_mapping'):
            mapping_type = self.meta.complex_mapping.mapping_type
            # Calculate expected ratio based on mapping type
            if mapping_type == '1:N':
                # For 1:N, typically expect more target rows
                expected_ratio = len(self.meta.complex_mapping.targets) / len(self.meta.complex_mapping.sources) if self.meta.complex_mapping.sources else None
            elif mapping_type == 'N:1':
                # For N:1, typically expect fewer target rows
                expected_ratio = len(self.meta.complex_mapping.targets) / len(self.meta.complex_mapping.sources) if self.meta.complex_mapping.sources else None
        
        for fn in CHECK_REGISTRY.get("volume", []):
            # Check if function accepts mapping_type parameter
            import inspect
            sig = inspect.signature(fn)
            if 'mapping_type' in sig.parameters:
                result = fn(
                    self.table_name,
                    self.src_df,
                    self.tgt_df,
                    self.volume_tolerance,
                    mapping_type=mapping_type,
                    expected_ratio=expected_ratio
                )
            else:
                # Backward compatibility with old signature
                result = fn(
                    self.table_name,
                    self.src_df,
                    self.tgt_df,
                    self.volume_tolerance,
                )
            self.results.extend(self._normalize_result(result))

        # -----------------------------
        # Aggregate checks
        # -----------------------------
        for col in getattr(self.meta, "aggregates", []):
            # Handle column mapping for complex mappings
            src_col = col
            tgt_col = col
            if hasattr(self.meta, 'aggregate_column_mapping') and self.meta.aggregate_column_mapping:
                # If target column is mapped, use the source column name
                if col in self.meta.aggregate_column_mapping.values():
                    # Find the source column name
                    src_col = next(k for k, v in self.meta.aggregate_column_mapping.items() if v == col)
                elif col in self.meta.aggregate_column_mapping:
                    # Target column is the key, source is the value
                    src_col = self.meta.aggregate_column_mapping[col]
            
            # Check if columns exist in dataframes
            if src_col not in self.src_df.columns:
                from core.result import TestResult
                from core.enums import CheckStatus
                self.results.append(TestResult(
                    name=f"Aggregate Check: {self.table_name} - {col}",
                    status=CheckStatus.WARN,
                    message=f"Source column '{src_col}' not found in source data for aggregate check."
                ))
                continue
            
            if tgt_col not in self.tgt_df.columns:
                from core.result import TestResult
                from core.enums import CheckStatus
                self.results.append(TestResult(
                    name=f"Aggregate Check: {self.table_name} - {col}",
                    status=CheckStatus.WARN,
                    message=f"Target column '{tgt_col}' not found in target data for aggregate check."
                ))
                continue
            
            for fn in CHECK_REGISTRY.get("aggregates", []):
                result = fn(
                    self.src_df,
                    self.tgt_df,
                    src_col,  # Use source column name
                    self.table_name,
                    self.aggregate_tolerance,
                )
                # Update result to show target column name if different
                if src_col != tgt_col and result:
                    if isinstance(result, list):
                        for r in result:
                            if hasattr(r, 'name'):
                                r.name = r.name.replace(src_col, f"{src_col}->{tgt_col}")
                    elif hasattr(result, 'name'):
                        result.name = result.name.replace(src_col, f"{src_col}->{tgt_col}")
                self.results.extend(self._normalize_result(result))

        # -----------------------------
        # Mapping checks
        # -----------------------------
        for mapping in getattr(self.meta, "mappings", []):
            for fn in CHECK_REGISTRY.get("mappings", []):
                result = fn(
                    self.tgt_df,
                    mapping.columns,
                    mapping.allowed_values,
                    self.table_name,
                )
                self.results.extend(self._normalize_result(result))

        # -----------------------------
        # Relationship checks
        # -----------------------------
        for relation in getattr(self.meta, "relationships", []):
            child_df = load_table(relation.child["target"])
            parent_df = load_table(relation.parent["target"])

            for fn in CHECK_REGISTRY.get("relationships", []):
                result = fn(
                    child_df,
                    parent_df,
                    relation.child["fk_column"],
                    relation.parent["pk_column"],
                    self.table_name,
                )
                self.results.extend(self._normalize_result(result))

        # -----------------------------
        # Data constraint checks
        # -----------------------------
        for col, constraints in getattr(self.meta, "data_constraints", {}).items():
            if isinstance(constraints, str):
                constraints = [constraints]

            result = check_data_constraints(
                self.tgt_df,
                {col: constraints},
                self.table_name,
            )
            self.results.extend(self._normalize_result(result))

        return self.results
