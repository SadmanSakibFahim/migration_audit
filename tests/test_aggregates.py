import pandas as pd
from checks.aggregates import check_sum
from core.enums import CheckStatus

def test_sum_exact_match():
    src = pd.DataFrame({"amount": [10, 20, 30]})
    tgt = pd.DataFrame({"amount": [10, 20, 30]})

    result = check_sum(src, tgt, "amount", "orders", tolerance=0.1)

    assert result.status == CheckStatus.PASS

def test_sum_zero_source_warn():
    src = pd.DataFrame({"amount": [0, 0, 0]})
    tgt = pd.DataFrame({"amount": [0, 1, 2]})

    result = check_sum(src, tgt, "amount", "orders", tolerance=1.0)

    assert result.status == CheckStatus.WARN
