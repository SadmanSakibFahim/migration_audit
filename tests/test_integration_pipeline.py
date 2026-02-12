"""Integration Pipeline Tests — Chris Traeger (T013)

Cross-component integration tests validating the interplay between
DataSource, CheckRunner, Verdict, and Sanitizer.
"""
import pytest
import os
import tempfile
import pandas as pd
from core.audit.check_runner import CheckRunner
from core.audit.verdict import final_verdict, Verdict, is_migration_allowed
from core.audit.enums import CheckStatus
from core.audit.config_models import TableConfig, MappingConfig
from core.db.data_source import create_data_source, CSVDataSource
from core.sanitization.masking import DataSanitizer


# ===================================================================
# DataSource → CheckRunner → Verdict Pipeline
# ===================================================================

class TestDataSourceToVerdict:
    def test_csv_to_verdict_happy_path(self, tmp_path):
        """CSV files → DataSource → CheckRunner → Verdict.GO."""
        # Create temp CSV files
        src_data = pd.DataFrame({"id": [1, 2, 3], "amount": [10.0, 20.0, 30.0]})
        tgt_data = pd.DataFrame({"id": [1, 2, 3], "amount": [10.0, 20.0, 30.0]})

        src_path = tmp_path / "src.csv"
        tgt_path = tmp_path / "tgt.csv"
        src_data.to_csv(src_path, index=False)
        tgt_data.to_csv(tgt_path, index=False)

        # Load via DataSource
        src_ds = create_data_source(str(src_path))
        tgt_ds = create_data_source(str(tgt_path))

        src_df = src_ds.load()
        tgt_df = tgt_ds.load()

        # Run audit
        meta = TableConfig(
            source=str(src_path),
            target=str(tgt_path),
            primary_key="id",
            aggregates=["amount"],
        )
        runner = CheckRunner("integration_test", meta, src_df, tgt_df)
        results = runner.execute_all()
        verdict = final_verdict(results)

        assert verdict == Verdict.GO
        assert is_migration_allowed(verdict) is True

    def test_csv_mismatch_gives_no_go(self, tmp_path):
        """Mismatched CSVs → DataSource → CheckRunner → NO-GO."""
        src_data = pd.DataFrame({"id": range(100), "amount": range(100)})
        tgt_data = pd.DataFrame({"id": range(50), "amount": range(50)})

        src_path = tmp_path / "src.csv"
        tgt_path = tmp_path / "tgt.csv"
        src_data.to_csv(src_path, index=False)
        tgt_data.to_csv(tgt_path, index=False)

        src_df = create_data_source(str(src_path)).load()
        tgt_df = create_data_source(str(tgt_path)).load()

        meta = TableConfig(
            source=str(src_path),
            target=str(tgt_path),
            primary_key="id",
        )
        runner = CheckRunner("mismatch_test", meta, src_df, tgt_df, volume_tolerance=0.1)
        results = runner.execute_all()
        verdict = final_verdict(results)

        assert verdict == Verdict.NO_GO
        assert is_migration_allowed(verdict) is False


# ===================================================================
# DataSource → Sanitizer Pipeline
# ===================================================================

class TestDataSourceToSanitizer:
    def test_csv_load_then_sanitize(self, tmp_path):
        """Load CSV with PII, sanitize, verify PII is masked."""
        raw = pd.DataFrame({
            "email": ["real@person.com", "ceo@corp.com"],
            "ssn": ["123-45-6789", "987-65-4321"],
            "amount": [100, 200],
        })
        csv_path = tmp_path / "pii_data.csv"
        raw.to_csv(csv_path, index=False)

        ds = create_data_source(str(csv_path))
        df = ds.load()

        sanitizer = DataSanitizer()
        clean = sanitizer.sanitize(df)

        assert "ssn" not in clean.columns
        assert clean["email"][0] != "real@person.com"
        assert clean["amount"][0] == 100

    def test_sanitizer_on_audit_results(self):
        """Sanitize a DataFrame that resembles audit output."""
        output = pd.DataFrame({
            "check_name": ["Volume", "Identity"],
            "status": ["PASS", "FAIL"],
            "email": ["admin@co.com", "ops@co.com"],
        })
        sanitizer = DataSanitizer()
        clean = sanitizer.sanitize(output)

        assert clean["email"][0] != "admin@co.com"
        assert clean["check_name"][0] == "Volume"


# ===================================================================
# Full Pipeline: CSV → Audit → Sanitize → Verdic
# ===================================================================

class TestFullPipeline:
    def test_end_to_end_with_sanitizer(self, tmp_path):
        """Full pipeline: create CSVs → load → audit → verdict → sanitize report."""
        src = pd.DataFrame({
            "id": [1, 2, 3],
            "email": ["a@x.com", "b@x.com", "c@x.com"],
            "amount": [10, 20, 30],
        })
        tgt = src.copy()

        src_path = tmp_path / "src.csv"
        tgt_path = tmp_path / "tgt.csv"
        src.to_csv(src_path, index=False)
        tgt.to_csv(tgt_path, index=False)

        # Step 1: Load
        src_df = create_data_source(str(src_path)).load()
        tgt_df = create_data_source(str(tgt_path)).load()

        # Step 2: Audit
        meta = TableConfig(
            source=str(src_path),
            target=str(tgt_path),
            primary_key="id",
            aggregates=["amount"],
        )
        runner = CheckRunner("full_pipeline", meta, src_df, tgt_df)
        results = runner.execute_all()

        # Step 3: Verdict
        verdict = final_verdict(results)
        assert verdict == Verdict.GO

        # Step 4: Sanitize the original data (simulating report export)
        sanitizer = DataSanitizer()
        clean = sanitizer.sanitize(tgt_df)
        assert clean["email"][0] != "a@x.com"
        assert clean["amount"][0] == 10


# ===================================================================
# DataSource Validation
# ===================================================================

class TestDataSourceValidation:
    def test_csv_datasource_validates(self, tmp_path):
        """CSVDataSource.validate() checks file existence."""
        # Existing file
        path = tmp_path / "exists.csv"
        pd.DataFrame({"a": [1]}).to_csv(path, index=False)
        ds = CSVDataSource(str(path))
        assert ds.validate() is True

    def test_csv_datasource_invalid_path(self):
        """CSVDataSource with non-existent path raises FileNotFoundError."""
        ds = CSVDataSource("/nonexistent/path/fake.csv")
        with pytest.raises(FileNotFoundError):
            ds.validate()
