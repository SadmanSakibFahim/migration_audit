"""Aggregate Check Tests — Leslie Knope (T014)

Expanded coverage for all 5 aggregate functions:
  check_sum, check_avg, check_max, check_min, check_variance
"""

import pandas as pd

from checks.aggregates import (check_avg, check_max, check_min, check_sum,
                               check_variance)
from core.audit.enums import CheckStatus

# ===================================================================
# check_sum
# ===================================================================


class TestCheckSum:
    def test_exact_match_pass(self):
        src = pd.DataFrame({"amount": [10, 20, 30]})
        tgt = pd.DataFrame({"amount": [10, 20, 30]})
        result = check_sum(src, tgt, "amount", "orders", tolerance=0.1)
        assert result.status == CheckStatus.PASS

    def test_within_tolerance_warns(self):
        src = pd.DataFrame({"amount": [100, 200, 300]})
        tgt = pd.DataFrame({"amount": [100, 200, 299]})  # 0.17% drift
        result = check_sum(src, tgt, "amount", "orders", tolerance=1.0)
        assert result.status == CheckStatus.WARN

    def test_exceeds_tolerance_fail(self):
        src = pd.DataFrame({"amount": [100, 200, 300]})
        tgt = pd.DataFrame({"amount": [100, 200, 200]})  # 16.7% drift
        result = check_sum(src, tgt, "amount", "orders", tolerance=1.0)
        assert result.status == CheckStatus.FAIL

    def test_zero_source_warn(self):
        src = pd.DataFrame({"amount": [0, 0, 0]})
        tgt = pd.DataFrame({"amount": [0, 1, 2]})
        result = check_sum(src, tgt, "amount", "orders", tolerance=1.0)
        assert result.status == CheckStatus.WARN

    def test_both_zero_warns(self):
        """When source sum is 0, check_sum returns WARN regardless."""
        src = pd.DataFrame({"amount": [0, 0]})
        tgt = pd.DataFrame({"amount": [0, 0]})
        result = check_sum(src, tgt, "amount", "orders", tolerance=0.1)
        assert result.status == CheckStatus.WARN


# ===================================================================
# check_avg
# ===================================================================


class TestCheckAvg:
    def test_exact_match_pass(self):
        src = pd.DataFrame({"val": [10, 20, 30]})
        tgt = pd.DataFrame({"val": [10, 20, 30]})
        result = check_avg(src, tgt, "val", "test", tolerance=0.1)
        assert result.status == CheckStatus.PASS

    def test_within_tolerance_warns(self):
        src = pd.DataFrame({"val": [100, 200]})
        tgt = pd.DataFrame({"val": [100, 201]})  # avg: 150 vs 150.5 = 0.33%
        result = check_avg(src, tgt, "val", "test", tolerance=1.0)
        assert result.status == CheckStatus.WARN

    def test_exceeds_tolerance_fail(self):
        src = pd.DataFrame({"val": [10, 20]})
        tgt = pd.DataFrame({"val": [10, 50]})  # avg: 15 vs 30 = 100%
        result = check_avg(src, tgt, "val", "test", tolerance=1.0)
        assert result.status == CheckStatus.FAIL

    def test_zero_source_avg_warn(self):
        src = pd.DataFrame({"val": [0, 0]})
        tgt = pd.DataFrame({"val": [0, 5]})
        result = check_avg(src, tgt, "val", "test", tolerance=1.0)
        assert result.status == CheckStatus.WARN


# ===================================================================
# check_max
# ===================================================================


class TestCheckMax:
    def test_exact_match_pass(self):
        src = pd.DataFrame({"val": [10, 20, 30]})
        tgt = pd.DataFrame({"val": [10, 20, 30]})
        result = check_max(src, tgt, "val", "test", tolerance=0.1)
        assert result.status == CheckStatus.PASS

    def test_within_tolerance_warns(self):
        src = pd.DataFrame({"val": [100]})
        tgt = pd.DataFrame({"val": [100.5]})  # 0.5% drift
        result = check_max(src, tgt, "val", "test", tolerance=1.0)
        assert result.status == CheckStatus.WARN

    def test_exceeds_tolerance_fail(self):
        src = pd.DataFrame({"val": [100]})
        tgt = pd.DataFrame({"val": [200]})  # 100% drift
        result = check_max(src, tgt, "val", "test", tolerance=1.0)
        assert result.status == CheckStatus.FAIL


# ===================================================================
# check_min
# ===================================================================


class TestCheckMin:
    def test_exact_match_pass(self):
        src = pd.DataFrame({"val": [10, 20, 30]})
        tgt = pd.DataFrame({"val": [10, 20, 30]})
        result = check_min(src, tgt, "val", "test", tolerance=0.1)
        assert result.status == CheckStatus.PASS

    def test_within_tolerance_warns(self):
        src = pd.DataFrame({"val": [100, 200]})
        tgt = pd.DataFrame({"val": [99.5, 200]})  # 0.5% drift
        result = check_min(src, tgt, "val", "test", tolerance=1.0)
        assert result.status == CheckStatus.WARN

    def test_exceeds_tolerance_fail(self):
        src = pd.DataFrame({"val": [100]})
        tgt = pd.DataFrame({"val": [50]})  # 50% drift
        result = check_min(src, tgt, "val", "test", tolerance=1.0)
        assert result.status == CheckStatus.FAIL


# ===================================================================
# check_variance
# ===================================================================


class TestCheckVariance:
    def test_exact_match_pass(self):
        src = pd.DataFrame({"val": [10, 20, 30]})
        tgt = pd.DataFrame({"val": [10, 20, 30]})
        result = check_variance(src, tgt, "val", "test", tolerance=0.1)
        assert result.status == CheckStatus.PASS

    def test_within_tolerance_warns(self):
        src = pd.DataFrame({"val": [10, 20, 30, 40, 50]})
        tgt = pd.DataFrame({"val": [10, 20, 30, 40, 50.3]})  # tiny variance shift
        result = check_variance(src, tgt, "val", "test", tolerance=5.0)
        assert result.status == CheckStatus.WARN

    def test_exceeds_tolerance_fail(self):
        src = pd.DataFrame({"val": [10, 10, 10]})  # variance = 0
        tgt = pd.DataFrame({"val": [1, 10, 100]})  # large variance
        result = check_variance(src, tgt, "val", "test", tolerance=1.0)
        # When source var = 0 and target var > 0, should warn or fail
        assert result.status in (CheckStatus.WARN, CheckStatus.FAIL)
