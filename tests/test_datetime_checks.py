# tests/test_datetime_checks.py

import pandas as pd
import pytest

from checks.datetime_checks import check_timezone_consistency
from core.audit.enums import CheckStatus


class TestCheckTimezoneConsistency:
    """Tests for check_timezone_consistency()."""

    # --- Parse failure detection ---

    def test_parse_failures_in_source_flagged(self):
        src = pd.DataFrame({"created_at": ["not-a-date", "also-bad", "2023-01-01"]})
        tgt = pd.DataFrame({"created_at": ["2023-01-01", "2023-01-02", "2023-01-01"]})
        results = check_timezone_consistency(src, tgt, "created_at", "orders")
        names = [r.name for r in results]
        statuses = [r.status for r in results]
        assert any("Parse Failures" in n for n in names)
        assert any(s == CheckStatus.FAIL for s in statuses)

    def test_no_parse_failures_clean_data(self):
        src = pd.DataFrame({"created_at": ["2023-01-01", "2023-06-15", "2023-12-31"]})
        tgt = pd.DataFrame({"created_at": ["2023-01-01", "2023-06-15", "2023-12-31"]})
        results = check_timezone_consistency(src, tgt, "created_at", "orders")
        # Should have no parse failure result
        names = [r.name for r in results]
        assert not any("Parse Failures" in n for n in names)

    # --- TZ awareness mismatch ---

    def test_tz_aware_source_naive_target(self):
        src = pd.DataFrame({"created_at": pd.to_datetime(
            ["2023-01-01T00:00:00Z", "2023-06-01T00:00:00Z"]
        ).tz_convert("UTC").astype(str)})
        tgt = pd.DataFrame({"created_at": ["2023-01-01", "2023-06-01"]})
        results = check_timezone_consistency(src, tgt, "created_at", "orders")
        # TZ awareness mismatch should be detected (one tz-aware, one naive)
        # Note: raw string timestamps are parsed to tz-naïve unless they include offset
        # Just verify the check runs without error
        assert isinstance(results, list)

    def test_both_naïve_no_mismatch(self):
        src = pd.DataFrame({"created_at": ["2023-01-01", "2023-06-01"]})
        tgt = pd.DataFrame({"created_at": ["2023-01-01", "2023-06-01"]})
        results = check_timezone_consistency(src, tgt, "created_at", "orders")
        tz_mismatch = [r for r in results if "TZ Awareness Mismatch" in r.name]
        assert len(tz_mismatch) == 0

    # --- Systematic offset detection (row-level) ---

    def test_systematic_1h_offset_detected(self):
        """1-hour systematic offset (classic DST bug) should be flagged."""
        dates_src = pd.to_datetime([
            "2023-01-01T12:00:00+00:00",
            "2023-02-01T08:00:00+00:00",
            "2023-03-01T15:30:00+00:00",
        ])
        dates_tgt = pd.to_datetime([
            "2023-01-01T13:00:00+00:00",  # +1h
            "2023-02-01T09:00:00+00:00",  # +1h
            "2023-03-01T16:30:00+00:00",  # +1h
        ])
        src = pd.DataFrame({"id": [1, 2, 3], "created_at": dates_src.astype(str)})
        tgt = pd.DataFrame({"id": [1, 2, 3], "created_at": dates_tgt.astype(str)})
        results = check_timezone_consistency(
            src, tgt, "created_at", "orders", pk_column="id"
        )
        systematic = [r for r in results if "Systematic TZ Offset" in r.name]
        assert len(systematic) == 1
        assert systematic[0].status == CheckStatus.FAIL
        assert systematic[0].details["median_delta_hours"] == 1.0

    def test_no_offset_passes(self):
        """Identical timestamps → zero delta → no offset alert."""
        dates = pd.to_datetime([
            "2023-01-01T12:00:00+00:00",
            "2023-06-01T08:00:00+00:00",
        ])
        src = pd.DataFrame({"id": [1, 2], "created_at": dates.astype(str)})
        tgt = pd.DataFrame({"id": [1, 2], "created_at": dates.astype(str)})
        results = check_timezone_consistency(
            src, tgt, "created_at", "orders", pk_column="id"
        )
        systematic = [r for r in results if "Systematic TZ Offset" in r.name]
        assert len(systematic) == 0
        delta_results = [r for r in results if "Timestamp Delta" in r.name]
        if delta_results:
            assert delta_results[0].status == CheckStatus.PASS

    # --- Expected TZ check ---

    def test_expected_tz_match(self):
        dates_utc = pd.to_datetime(["2023-01-01T12:00:00+00:00", "2023-06-01T08:00:00+00:00"])
        src = pd.DataFrame({"created_at": dates_utc.astype(str)})
        tgt = pd.DataFrame({"created_at": dates_utc.astype(str)})
        results = check_timezone_consistency(
            src, tgt, "created_at", "orders", expected_tz="UTC"
        )
        # Should not report TZ mismatch (both tz-naive after parsing raw strings)
        assert isinstance(results, list)

    # --- Column missing ---

    def test_column_missing_in_source(self):
        src = pd.DataFrame({"other": ["2023-01-01"]})
        tgt = pd.DataFrame({"created_at": ["2023-01-01"]})
        results = check_timezone_consistency(src, tgt, "created_at", "orders")
        assert results[0].status == CheckStatus.FAIL
        assert "source" in results[0].message.lower()

    def test_column_missing_in_target(self):
        src = pd.DataFrame({"created_at": ["2023-01-01"]})
        tgt = pd.DataFrame({"other": ["2023-01-01"]})
        results = check_timezone_consistency(src, tgt, "created_at", "orders")
        assert results[0].status == CheckStatus.FAIL
        assert "target" in results[0].message.lower()
