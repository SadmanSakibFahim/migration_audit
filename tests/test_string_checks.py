# tests/test_string_checks.py
# Ron said it was excessive. Ron is wrong."

import pandas as pd
import pytest

from checks.string_checks import (
    check_string_truncation,
    check_whitespace_corruption,
    check_encoding_corruption
)
from core.audit.enums import CheckStatus


class TestCheckStringTruncation:
    """Tests for check_string_truncation()."""

    def _src(self, values):
        return pd.DataFrame({"description": values})

    def _tgt(self, values):
        return pd.DataFrame({"description": values})

    # --- PASS cases ---

    def test_no_truncation_within_limit(self):
        src = self._src(["hello", "world", "foo"])
        tgt = self._tgt(["hello", "world", "foo"])
        results = check_string_truncation(src, tgt, "description", "orders")
        assert len(results) == 1
        assert results[0].status == CheckStatus.PASS

    def test_no_truncation_with_declared_max_length(self):
        src = self._src(["abc", "de", "f"])
        tgt = self._tgt(["abc", "de", "f"])
        results = check_string_truncation(src, tgt, "description", "orders", max_length=10)
        assert results[0].status == CheckStatus.PASS

    # --- FAIL cases ---

    def test_truncation_detected_by_declared_max(self):
        src = self._src(["A" * 300, "B" * 200, "short"])
        tgt = self._tgt(["A" * 255, "B" * 200, "short"])
        results = check_string_truncation(src, tgt, "description", "orders", max_length=255)
        assert results[0].status == CheckStatus.FAIL
        assert "300" in results[0].message or "1" in results[0].message
        assert results[0].details["rows_exceeding_limit"] == 1

    def test_truncation_detected_all_rows(self):
        src = self._src(["A" * 300, "B" * 400])
        tgt = self._tgt(["A" * 255, "B" * 255])
        results = check_string_truncation(src, tgt, "description", "orders", max_length=255)
        assert results[0].status == CheckStatus.FAIL
        assert results[0].details["rows_exceeding_limit"] == 2

    def test_truncation_detected_by_target_max(self):
        # No declared max_length — infer from target max observed length (255)
        src = self._src(["A" * 300, "normal"])
        tgt = self._tgt(["A" * 255, "normal"])
        results = check_string_truncation(src, tgt, "description", "orders")
        assert results[0].status == CheckStatus.FAIL

    # --- WARN cases ---

    def test_warn_when_src_max_greater_than_tgt_max_no_current_overflow(self):
        # Source has historically longer values than target max, but none exceed right now
        src = self._src(["A" * 200, "B" * 100])
        tgt = self._tgt(["A" * 150, "B" * 100])
        results = check_string_truncation(src, tgt, "description", "orders", max_length=255)
        assert results[0].status == CheckStatus.WARN

    # --- FAIL: column not found ---

    def test_column_missing_in_source(self):
        src = pd.DataFrame({"other_col": ["a", "b"]})
        tgt = pd.DataFrame({"description": ["a", "b"]})
        results = check_string_truncation(src, tgt, "description", "orders")
        assert results[0].status == CheckStatus.FAIL
        assert "source" in results[0].message.lower()

    def test_column_missing_in_target(self):
        src = pd.DataFrame({"description": ["a", "b"]})
        tgt = pd.DataFrame({"other_col": ["a", "b"]})
        results = check_string_truncation(src, tgt, "description", "orders")
        assert results[0].status == CheckStatus.FAIL
        assert "target" in results[0].message.lower()

    # --- Edge cases ---

    def test_empty_source_column(self):
        src = pd.DataFrame({"description": [None, None]})
        tgt = pd.DataFrame({"description": ["a", "b"]})
        results = check_string_truncation(src, tgt, "description", "orders")
        assert results[0].status == CheckStatus.WARN

    def test_numeric_column_coerced_to_str(self):
        """Numeric values should be coerced to string and length-checked correctly."""
        src = pd.DataFrame({"description": [12345678, 9]})
        tgt = pd.DataFrame({"description": [12345678, 9]})
        results = check_string_truncation(src, tgt, "description", "orders", max_length=5)
        # "12345678" is 8 chars > 5, "9" is 1 char. 1 row exceeds.
        assert results[0].status == CheckStatus.FAIL
        assert results[0].details["rows_exceeding_limit"] == 1


class TestCheckWhitespaceCorruption:
    def test_whitespace_normalization_warn(self):
        src = pd.DataFrame({"col": [" a ", "b", " c"]})
        tgt = pd.DataFrame({"col": ["a", "b", "c"]})
        results = check_whitespace_corruption(src, tgt, "col", "tbl")
        assert results[0].status == CheckStatus.WARN

    def test_whitespace_corruption_fail(self):
        src = pd.DataFrame({"col": ["a", "b", "c"]})
        tgt = pd.DataFrame({"col": [" a ", "b", "c"]})
        results = check_whitespace_corruption(src, tgt, "col", "tbl")
        assert results[0].status == CheckStatus.FAIL


class TestCheckEncodingCorruption:
    def test_encoding_corruption_fail(self):
        src = pd.DataFrame({"col": ["café", "naïve"]})
        tgt = pd.DataFrame({"col": ["cafÃ©", "naÃ¯ve"]})
        results = check_encoding_corruption(src, tgt, "col", "tbl")
        assert results[0].status == CheckStatus.FAIL

    def test_encoding_normalization_warn(self):
        src = pd.DataFrame({"col": ["cafÃ©", "naÃ¯ve"]})
        tgt = pd.DataFrame({"col": ["café", "naïve"]})
        results = check_encoding_corruption(src, tgt, "col", "tbl")
        assert results[0].status == CheckStatus.WARN

