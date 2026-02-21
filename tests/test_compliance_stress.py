"""Compliance Stress Tests — Chris Traeger (T013)

Stress testing and performance benchmarks for compliance features.
"""

import time

import pandas as pd
import pytest

from core.sanitization.masking import DataSanitizer


@pytest.fixture
def sanitizer():
    return DataSanitizer()


# ===================================================================
# Large Dataset Masking Performance
# ===================================================================


class TestLargeDatasetMasking:
    def test_100k_rows_completes_in_time(self, sanitizer):
        """Masking 100K rows should complete within 30 seconds."""
        n = 100_000
        df = pd.DataFrame(
            {
                "email": [f"user{i}@example.com" for i in range(n)],
                "username": [f"user_{i}" for i in range(n)],
                "normal_col": range(n),
            }
        )

        start = time.time()
        result = sanitizer.sanitize(df)
        elapsed = time.time() - start

        assert len(result) == n
        assert elapsed < 30, f"Masking took {elapsed:.1f}s (> 30s budget)"
        assert result["email"][0] != df["email"][0]  # Actually masked

    def test_10k_rows_with_all_pii_columns(self, sanitizer):
        """All 5 PII columns + 4 sensitive columns on 10K rows."""
        n = 10_000
        df = pd.DataFrame(
            {
                "email": [f"u{i}@x.com" for i in range(n)],
                "username": [f"user{i}" for i in range(n)],
                "user_id": [f"UID{i}" for i in range(n)],
                "customer_email": [f"cx{i}@x.com" for i in range(n)],
                "patient_id": [f"PAT{i}" for i in range(n)],
                "ssn": [f"000-00-{i:04d}" for i in range(n)],
                "credit_card": [f"4111-{i:04d}" for i in range(n)],
                "password": [f"hash{i}" for i in range(n)],
                "medical_record_number": [f"MRN{i}" for i in range(n)],
                "safe_col": range(n),
            }
        )

        result = sanitizer.sanitize(df)

        # Sensitive columns dropped
        assert "ssn" not in result.columns
        assert "credit_card" not in result.columns
        assert "password" not in result.columns
        assert "medical_record_number" not in result.columns

        # PII columns hashed
        assert len(result["email"][0]) == 64
        assert result["safe_col"][0] == 0

        # Row count preserved
        assert len(result) == n

    def test_shape_preserved(self, sanitizer):
        """Column count changes but row count stays the same."""
        n = 5_000
        df = pd.DataFrame(
            {
                "email": [f"u{i}@x.com" for i in range(n)],
                "ssn": ["000-00-0000"] * n,
                "data": range(n),
            }
        )
        result = sanitizer.sanitize(df)
        assert len(result) == n
        # One column dropped (ssn), so 2 remaining
        assert len(result.columns) == 2


# ===================================================================
# Repeated Masking Idempotency
# ===================================================================


class TestMaskingIdempotency:
    def test_double_sanitize_is_stable(self, sanitizer):
        """Sanitizing an already-sanitized DataFrame should not crash or corrupt."""
        df = pd.DataFrame({"email": ["test@x.com"], "data": [42]})
        pass1 = sanitizer.sanitize(df)
        pass2 = sanitizer.sanitize(pass1)

        # Email is hashed twice (hash of hash) — just ensure no crash
        assert len(pass2) == 1
        assert "data" in pass2.columns

    def test_sanitize_with_empty_columns(self, sanitizer):
        """DataFrame with all-empty PII columns handles gracefully."""
        df = pd.DataFrame({"email": [None, None, None], "data": [1, 2, 3]})
        result = sanitizer.sanitize(df)
        assert len(result) == 3
