from checks.relationships import check_links
from core.audit.enums import CheckStatus
import pandas as pd

def test_relationship_no_orphans():
    child = pd.DataFrame({"user_id": [1, 2, 3]})
    parent = pd.DataFrame({"id": [1, 2, 3]})

    result = check_links(
        child, parent,
        fk_column="user_id",
        pk_column="id",
        table_name="orders"
    )

    assert result.status == CheckStatus.PASS
