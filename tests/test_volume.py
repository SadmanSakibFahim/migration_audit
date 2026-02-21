import pandas as pd

from checks.volume import check_volume
from core.audit.enums import CheckStatus


def test_volume_exact_match_pass():
    src = pd.DataFrame({"id": [1, 2, 3]})
    tgt = pd.DataFrame({"id": [10, 20, 30]})

    result = check_volume("users", src, tgt, tolerance_pct=0.1)

    assert result.status == CheckStatus.PASS
    assert result.metrics["src_rows"] == 3
    assert result.metrics["tgt_rows"] == 3
    assert result.metrics["difference"] == 0
    assert result.metrics["tolerance"] == 0.1


def test_volume_with_empty_target_fails():
    src = pd.DataFrame({"id": [1, 2, 3]})
    tgt = pd.DataFrame(columns=["id"])

    result = check_volume("users", src, tgt, tolerance_pct=0.1)

    assert result.status == CheckStatus.FAIL
    assert result.metrics["src_rows"] == 3
    assert result.metrics["tgt_rows"] == 0
    assert result.metrics["difference"] == 3
    assert result.metrics["tolerance"] == 0.1


def test_volume_within_tolerance_pass():
    src = pd.DataFrame({"id": [1, 2, 3, 4, 5]})
    tgt = pd.DataFrame({"id": [10, 20, 30, 40]})

    result = check_volume("users", src, tgt, tolerance_pct=25.0)

    assert result.status == CheckStatus.PASS
    assert result.metrics["src_rows"] == 5
    assert result.metrics["tgt_rows"] == 4
    assert result.metrics["difference"] == 1
    assert result.metrics["tolerance"] == 25.0


def test_volume_exceeds_tolerance_fails():
    src = pd.DataFrame({"id": [1, 2, 3, 4, 5, 6]})
    tgt = pd.DataFrame({"id": [10, 20, 30]})

    result = check_volume("users", src, tgt, tolerance_pct=0.2)

    assert result.status == CheckStatus.FAIL
    assert result.metrics["src_rows"] == 6
    assert result.metrics["tgt_rows"] == 3
    assert result.metrics["difference"] == 3
    assert result.metrics["tolerance"] == 0.2


def test_volume_with_empty_source_warns():
    src = pd.DataFrame(columns=["id"])
    tgt = pd.DataFrame({"id": [1, 2]})

    result = check_volume("users", src, tgt, tolerance_pct=0.1)

    assert result.status == CheckStatus.WARN
    assert result.metrics["src_rows"] == 0
    assert result.metrics["tgt_rows"] == 2
    assert result.metrics["difference"] == 2
    assert result.metrics["tolerance"] == 0.1


def test_volume_both_empty_pass():
    src = pd.DataFrame(columns=["id"])
    tgt = pd.DataFrame(columns=["id"])

    result = check_volume("users", src, tgt, tolerance_pct=0.1)

    assert result.status == CheckStatus.PASS
    assert result.metrics["src_rows"] == 0
    assert result.metrics["tgt_rows"] == 0
    assert result.metrics["difference"] == 0
    assert result.metrics["tolerance"] == 0.1


def test_volume_large_datasets_pass():
    src = pd.DataFrame({"id": range(1000000)})
    tgt = pd.DataFrame({"id": range(990000)})

    result = check_volume("users", src, tgt, tolerance_pct=2.0)

    assert result.status == CheckStatus.PASS
    assert result.metrics["src_rows"] == 1000000
    assert result.metrics["tgt_rows"] == 990000
    assert result.metrics["difference"] == 10000
    assert result.metrics["tolerance"] == 2.0


def test_volume_large_datasets_fail():
    src = pd.DataFrame({"id": range(1000000)})
    tgt = pd.DataFrame({"id": range(950000)})

    result = check_volume("users", src, tgt, tolerance_pct=2.0)

    assert result.status == CheckStatus.FAIL
    assert result.metrics["src_rows"] == 1000000
    assert result.metrics["tgt_rows"] == 950000
    assert result.metrics["difference"] == 50000
    assert result.metrics["tolerance"] == 2.0


def test_volume_negative_tolerance_raises():
    src = pd.DataFrame({"id": [1, 2, 3]})
    tgt = pd.DataFrame({"id": [1, 2, 3]})

    try:
        check_volume("users", src, tgt, tolerance_pct=-0.1)
    except ValueError as e:
        assert str(e) == "Tolerance must be non-negative"


def test_volume_zero_tolerance_strict_match():
    src = pd.DataFrame({"id": [1, 2, 3]})
    tgt = pd.DataFrame({"id": [1, 2, 3]})

    result = check_volume("users", src, tgt, tolerance_pct=0.0)

    assert result.status == CheckStatus.PASS
    assert result.metrics["src_rows"] == 3
    assert result.metrics["tgt_rows"] == 3
    assert result.metrics["difference"] == 0
    assert result.metrics["tolerance"] == 0.0


def test_volume_zero_tolerance_strict_mismatch():
    src = pd.DataFrame({"id": [1, 2, 3]})
    tgt = pd.DataFrame({"id": [1, 2]})

    result = check_volume("users", src, tgt, tolerance_pct=0.0)

    assert result.status == CheckStatus.FAIL
    assert result.metrics["src_rows"] == 3
    assert result.metrics["tgt_rows"] == 2
    assert result.metrics["difference"] == 1
    assert result.metrics["tolerance"] == 0.0
