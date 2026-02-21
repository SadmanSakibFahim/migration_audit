"""Extended Sanitizer Tests — Anne Perkins (T012)

Comprehensive PII masking and sensitive column dropping tests
for core/sanitization/masking.py DataSanitizer.
"""

import pandas as pd
import pytest

from core.sanitization.masking import DataSanitizer


@pytest.fixture
def sanitizer():
    return DataSanitizer()


# ===================================================================
# PII Hashing
# ===================================================================


class TestPIIHashing:
    def test_email_hashed(self, sanitizer):
        df = pd.DataFrame({"email": ["test@example.com"]})
        result = sanitizer.sanitize(df)
        assert result["email"][0] != "test@example.com"
        assert len(result["email"][0]) == 64  # SHA-256

    def test_username_hashed(self, sanitizer):
        df = pd.DataFrame({"username": ["alice"]})
        result = sanitizer.sanitize(df)
        assert result["username"][0] != "alice"
        assert len(result["username"][0]) == 64

    def test_user_id_hashed(self, sanitizer):
        df = pd.DataFrame({"user_id": ["U123"]})
        result = sanitizer.sanitize(df)
        assert result["user_id"][0] != "U123"

    def test_customer_email_hashed(self, sanitizer):
        df = pd.DataFrame({"customer_email": ["cx@test.com"]})
        result = sanitizer.sanitize(df)
        assert result["customer_email"][0] != "cx@test.com"

    def test_patient_id_hashed(self, sanitizer):
        df = pd.DataFrame({"patient_id": ["PAT-001"]})
        result = sanitizer.sanitize(df)
        assert result["patient_id"][0] != "PAT-001"

    def test_hash_deterministic(self, sanitizer):
        """Same input → same hash (no per-call salting in SHA-256)."""
        df1 = pd.DataFrame({"email": ["same@test.com"]})
        df2 = pd.DataFrame({"email": ["same@test.com"]})
        r1 = sanitizer.sanitize(df1)
        r2 = sanitizer.sanitize(df2)
        assert r1["email"][0] == r2["email"][0]

    def test_different_emails_different_hashes(self, sanitizer):
        df = pd.DataFrame({"email": ["a@x.com", "b@x.com"]})
        result = sanitizer.sanitize(df)
        assert result["email"][0] != result["email"][1]


# ===================================================================
# Sensitive Column Dropping
# ===================================================================


class TestSensitiveColumnDropping:
    def test_ssn_dropped(self, sanitizer):
        df = pd.DataFrame({"ssn": ["123-45-6789"], "name": ["Bob"]})
        result = sanitizer.sanitize(df)
        assert "ssn" not in result.columns
        assert "name" in result.columns

    def test_credit_card_dropped(self, sanitizer):
        df = pd.DataFrame({"credit_card": ["4111-1111-1111-1111"]})
        result = sanitizer.sanitize(df)
        assert "credit_card" not in result.columns

    def test_password_dropped(self, sanitizer):
        df = pd.DataFrame({"password": ["secret123"]})
        result = sanitizer.sanitize(df)
        assert "password" not in result.columns

    def test_medical_record_number_dropped(self, sanitizer):
        df = pd.DataFrame({"medical_record_number": ["MRN-001"]})
        result = sanitizer.sanitize(df)
        assert "medical_record_number" not in result.columns

    def test_multiple_sensitive_columns_all_dropped(self, sanitizer):
        df = pd.DataFrame(
            {
                "ssn": ["123"],
                "credit_card": ["456"],
                "password": ["789"],
                "safe_col": ["ok"],
            }
        )
        result = sanitizer.sanitize(df)
        assert "ssn" not in result.columns
        assert "credit_card" not in result.columns
        assert "password" not in result.columns
        assert "safe_col" in result.columns


# ===================================================================
# Edge Cases
# ===================================================================


class TestSanitizerEdgeCases:
    def test_none_input_returns_none(self, sanitizer):
        result = sanitizer.sanitize(None)
        assert result is None

    def test_empty_df_returns_empty(self, sanitizer):
        df = pd.DataFrame()
        result = sanitizer.sanitize(df)
        assert result is not None
        assert result.empty

    def test_no_pii_columns_unchanged(self, sanitizer):
        df = pd.DataFrame({"safe": ["value1"], "also_safe": [42]})
        result = sanitizer.sanitize(df)
        assert result["safe"][0] == "value1"
        assert result["also_safe"][0] == 42

    def test_numeric_pii_value_converted_to_string_then_hashed(self, sanitizer):
        """Numeric values in PII columns should be converted and hashed."""
        df = pd.DataFrame({"user_id": [12345]})
        result = sanitizer.sanitize(df)
        assert result["user_id"][0] != 12345
        assert isinstance(result["user_id"][0], str)
        assert len(result["user_id"][0]) == 64

    def test_original_df_not_mutated(self, sanitizer):
        """Sanitize should not modify the original DataFrame."""
        df = pd.DataFrame({"email": ["test@x.com"], "ssn": ["123"]})
        original_email = df["email"][0]
        _ = sanitizer.sanitize(df)
        assert "ssn" in df.columns  # Original still has ssn
        assert df["email"][0] == original_email  # Original not hashed

    def test_mixed_pii_and_sensitive(self, sanitizer):
        """DataFrame with both PII (hash) and sensitive (drop) columns."""
        df = pd.DataFrame(
            {
                "email": ["test@x.com"],
                "credit_card": ["4111"],
                "normal": ["ok"],
            }
        )
        result = sanitizer.sanitize(df)
        assert "credit_card" not in result.columns  # Dropped
        assert result["email"][0] != "test@x.com"  # Hashed
        assert result["normal"][0] == "ok"  # Untouched

    def test_row_count_preserved(self, sanitizer):
        """Sanitize preserves row count."""
        df = pd.DataFrame({"email": [f"u{i}@x.com" for i in range(100)]})
        result = sanitizer.sanitize(df)
        assert len(result) == 100
