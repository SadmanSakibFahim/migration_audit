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
        for fn in CHECK_REGISTRY.get("volume", []):
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
            for fn in CHECK_REGISTRY.get("aggregates", []):
                result = fn(
                    self.src_df,
                    self.tgt_df,
                    col,
                    self.table_name,
                    self.aggregate_tolerance,
                )
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
