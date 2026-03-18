# tests/test_null_sentinel_checks.py

import pandas as pd
import pytest

from checks.null_sentinel_checks import check_null_sentinel_equivalence
from core.audit.enums import CheckStatus


SENTINELS = [0, -1, "N/A", "", "NULL", "null"]


class TestCheckNullSentinelEquivalence:
    """Tests for check_null_sentinel_equivalence()."""

    # --- PASS cases ---

    def test_pass_identical_nulls_no_sentinels(self):
        src = pd.DataFrame({"customer_id": [1, None, 3, None]})
        tgt = pd.DataFrame({"customer_id": [1, None, 3, None]})
        results = check_null_sentinel_equivalence(src, tgt, "customer_id", "orders", SENTINELS)
        assert results[0].status == CheckStatus.PASS

    def test_pass_no_nulls_or_sentinels_anywhere(self):
        src = pd.DataFrame({"customer_id": [1, 2, 3, 4]})
        tgt = pd.DataFrame({"customer_id": [1, 2, 3, 4]})
        results = check_null_sentinel_equivalence(src, tgt, "customer_id", "orders", SENTINELS)
        assert results[0].status == CheckStatus.PASS

    # --- WARN: logical equivalence after normalization ---

    def test_warn_sentinel_converted_to_null_in_target(self):
        """Source has sentinel 0 where target has NULL — logically equivalent after normalization."""
        src = pd.DataFrame({"customer_id": [1, 0, 3, 0]})     # 0 means "no customer"
        tgt = pd.DataFrame({"customer_id": [1, None, 3, None]})  # NULL in target
        results = check_null_sentinel_equivalence(src, tgt, "customer_id", "orders", [0, -1])
        assert results[0].status == CheckStatus.WARN
        assert "logically equivalent" in results[0].message

    def test_warn_na_string_converted_to_null(self):
        src = pd.DataFrame({"notes": ["hello", "N/A", "world", "N/A"]})
        tgt = pd.DataFrame({"notes": ["hello", None, "world", None]})
        results = check_null_sentinel_equivalence(src, tgt, "notes", "customers", ["N/A", ""])
        assert results[0].status == CheckStatus.WARN

    def test_warn_multiple_sentinel_types(self):
        """Mix of sentinel representations across source and target."""
        src = pd.DataFrame({"score": [-1, 100, 0, 200]})       # -1 and 0 are sentinels
        tgt = pd.DataFrame({"score": [None, 100, None, 200]})   # completely replaced with NULL
        results = check_null_sentinel_equivalence(src, tgt, "score", "scores", [0, -1])
        assert results[0].status == CheckStatus.WARN

    # --- FAIL: data loss / genuine mismatch ---

    def test_fail_more_nulls_in_target_after_normalization(self):
        """Target has MORE nulls even after normalization — data was lost."""
        src = pd.DataFrame({"customer_id": [1, 2, 3, 4]})
        tgt = pd.DataFrame({"customer_id": [1, None, None, 4]})
        results = check_null_sentinel_equivalence(src, tgt, "customer_id", "orders", [0, -1])
        assert results[0].status == CheckStatus.FAIL

    def test_fail_fewer_nulls_in_target(self):
        """Target has FEWER nulls than source even after normalization — incorrect fill."""
        src = pd.DataFrame({"customer_id": [None, None, 3, 4]})
        tgt = pd.DataFrame({"customer_id": [1, 2, 3, 4]})
        results = check_null_sentinel_equivalence(src, tgt, "customer_id", "orders", [0, -1])
        assert results[0].status == CheckStatus.FAIL

    # --- Column missing ---

    def test_column_missing_in_source(self):
        src = pd.DataFrame({"other": [1, 2]})
        tgt = pd.DataFrame({"customer_id": [1, 2]})
        results = check_null_sentinel_equivalence(src, tgt, "customer_id", "orders", SENTINELS)
        assert results[0].status == CheckStatus.FAIL
        assert "source" in results[0].message.lower()

    def test_column_missing_in_target(self):
        src = pd.DataFrame({"customer_id": [1, 2]})
        tgt = pd.DataFrame({"other": [1, 2]})
        results = check_null_sentinel_equivalence(src, tgt, "customer_id", "orders", SENTINELS)
        assert results[0].status == CheckStatus.FAIL
        assert "target" in results[0].message.lower()

    # --- Edge cases ---

    def test_empty_dataframes(self):
        src = pd.DataFrame({"customer_id": []})
        tgt = pd.DataFrame({"customer_id": []})
        results = check_null_sentinel_equivalence(src, tgt, "customer_id", "orders", SENTINELS)
        assert results[0].status == CheckStatus.WARN   # empty → skip

    def test_empty_sentinel_list_passes_on_no_difference(self):
        src = pd.DataFrame({"customer_id": [None, 1, 2]})
        tgt = pd.DataFrame({"customer_id": [None, 1, 2]})
        results = check_null_sentinel_equivalence(src, tgt, "customer_id", "orders", [])
        assert results[0].status == CheckStatus.PASS

    def test_sentinel_details_in_result(self):
        src = pd.DataFrame({"customer_id": [0, 1, 2]})
        tgt = pd.DataFrame({"customer_id": [None, 1, 2]})
        results = check_null_sentinel_equivalence(src, tgt, "customer_id", "orders", [0])
        d = results[0].details
        assert "src_sentinel_substitutions" in d
        assert "tgt_sentinel_substitutions" in d
        assert d["src_sentinel_substitutions"] == 1
