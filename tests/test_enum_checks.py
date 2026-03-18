# tests/test_enum_checks.py

import pandas as pd
import pytest

from checks.enum_checks import (
    check_enum_equivalence,
    check_categorical_distribution,
    check_boolean_normalization
)
from core.audit.enums import CheckStatus


class TestCheckEnumEquivalence:
    """Tests for check_enum_equivalence()."""

    # --- Raw set comparison (no mapping) ---

    def test_raw_pass_identical_values(self):
        src = pd.DataFrame({"status": ["active", "inactive", "active"]})
        tgt = pd.DataFrame({"status": ["active", "inactive", "active"]})
        results = check_enum_equivalence(src, tgt, "status", "users")
        assert len(results) == 1
        assert results[0].status == CheckStatus.PASS

    def test_raw_fail_source_value_missing_in_target(self):
        src = pd.DataFrame({"status": ["active", "inactive", "pending"]})
        tgt = pd.DataFrame({"status": ["active", "inactive"]})
        results = check_enum_equivalence(src, tgt, "status", "users")
        assert results[0].status == CheckStatus.FAIL
        assert "pending" in results[0].message

    def test_raw_fail_target_has_extra_value(self):
        src = pd.DataFrame({"status": ["active", "inactive"]})
        tgt = pd.DataFrame({"status": ["A", "I", "X"]})
        results = check_enum_equivalence(src, tgt, "status", "users")
        assert results[0].status == CheckStatus.FAIL

    def test_raw_fail_both_sides_differ(self):
        src = pd.DataFrame({"status": ["active", "pending"]})
        tgt = pd.DataFrame({"status": ["A", "P", "X"]})
        results = check_enum_equivalence(src, tgt, "status", "users")
        assert results[0].status == CheckStatus.FAIL
        d = results[0].details
        assert len(d["in_source_not_target"]) > 0
        assert len(d["in_target_not_source"]) > 0

    # --- Mapping mode ---

    def test_mapping_pass_full_match(self):
        src = pd.DataFrame({"status": ["active", "inactive", "active"]})
        tgt = pd.DataFrame({"status": ["A", "I", "A"]})
        mapping = {"active": "A", "inactive": "I"}
        results = check_enum_equivalence(src, tgt, "status", "users", mapping=mapping)
        assert results[0].status == CheckStatus.PASS

    def test_mapping_fail_unmapped_source_value(self):
        src = pd.DataFrame({"status": ["active", "inactive", "pending"]})
        tgt = pd.DataFrame({"status": ["A", "I", "A"]})
        mapping = {"active": "A", "inactive": "I"}  # "pending" not mapped
        results = check_enum_equivalence(src, tgt, "status", "users", mapping=mapping)
        assert results[0].status == CheckStatus.FAIL
        assert "pending" in results[0].message
        assert results[0].details["unmapped_row_count"] == 1

    def test_mapping_fail_expected_value_missing_in_target(self):
        src = pd.DataFrame({"status": ["active", "inactive"]})
        tgt = pd.DataFrame({"status": ["A"]})  # "I" never appears in target
        mapping = {"active": "A", "inactive": "I"}
        results = check_enum_equivalence(src, tgt, "status", "users", mapping=mapping)
        assert results[0].status == CheckStatus.FAIL
        assert "I" in results[0].message

    def test_mapping_fail_orphaned_target_value(self):
        src = pd.DataFrame({"status": ["active", "inactive"]})
        tgt = pd.DataFrame({"status": ["A", "I", "Z"]})  # "Z" is unexpected
        mapping = {"active": "A", "inactive": "I"}
        results = check_enum_equivalence(src, tgt, "status", "users", mapping=mapping)
        assert results[0].status == CheckStatus.FAIL
        assert "Z" in results[0].message

    # --- Column missing ---

    def test_column_missing_in_source(self):
        src = pd.DataFrame({"other": ["a"]})
        tgt = pd.DataFrame({"status": ["A"]})
        results = check_enum_equivalence(src, tgt, "status", "users")
        assert results[0].status == CheckStatus.FAIL
        assert "source" in results[0].message.lower()

    def test_column_missing_in_target(self):
        src = pd.DataFrame({"status": ["active"]})
        tgt = pd.DataFrame({"other": ["A"]})
        results = check_enum_equivalence(src, tgt, "status", "users")
        assert results[0].status == CheckStatus.FAIL
        assert "target" in results[0].message.lower()

    # --- Null handling ---

    def test_nulls_ignored_in_raw_comparison(self):
        src = pd.DataFrame({"status": ["active", None, "inactive"]})
        tgt = pd.DataFrame({"status": ["active", None, "inactive"]})
        results = check_enum_equivalence(src, tgt, "status", "users")
        assert results[0].status == CheckStatus.PASS


class TestCheckCategoricalDistribution:
    """Tests for check_categorical_distribution()."""

    def test_distribution_stable_pass(self):
        src = pd.DataFrame({"type": ["A", "A", "B", "B"]})
        tgt = pd.DataFrame({"type": ["A", "A", "A", "B", "B", "B"]})
        results = check_categorical_distribution(src, tgt, "type", "users", tolerance_pct=0.05)
        assert results[0].status == CheckStatus.PASS

    def test_distribution_shift_warn(self):
        src = pd.DataFrame({"type": ["A"] * 90 + ["B"] * 10})
        tgt = pd.DataFrame({"type": ["A"] * 50 + ["B"] * 50})
        results = check_categorical_distribution(src, tgt, "type", "users", tolerance_pct=0.10)
        assert results[0].status == CheckStatus.WARN


class TestCheckBooleanNormalization:
    """Tests for check_boolean_normalization()."""

    def test_boolean_normalization_pass(self):
        src = pd.DataFrame({"is_active": ["Y", "Y", "N", "N"]})
        tgt = pd.DataFrame({"is_active": ["True", "True", "False", "False"]})
        true_vals = ["Y", "True"]
        false_vals = ["N", "False"]
        results = check_boolean_normalization(src, tgt, "is_active", "users", true_vals, false_vals)
        assert results[0].status == CheckStatus.PASS

    def test_boolean_normalization_fail_ratio_mismatch(self):
        src = pd.DataFrame({"is_active": ["Y", "Y", "Y", "N"]})
        tgt = pd.DataFrame({"is_active": ["True", "False", "False", "False"]})
        true_vals = ["Y", "True"]
        false_vals = ["N", "False"]
        results = check_boolean_normalization(src, tgt, "is_active", "users", true_vals, false_vals)
        assert results[0].status == CheckStatus.FAIL

