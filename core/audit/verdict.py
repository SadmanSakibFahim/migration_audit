from collections import Counter

from core.audit.enums import CheckStatus
from core.audit.logger import get_logger

logger = get_logger(__name__)


class Verdict:
    GO = "GO"
    GO_WITH_WARNINGS = "GO WITH WARNINGS"
    NO_GO = "NO-GO"
    ERROR = "ERROR"


def final_verdict(results):
    """
    Determine final migration verdict based on check results.

    Rules:
    - Any FAIL  -> NO-GO
    - No FAIL, at least one WARN -> GO WITH WARNINGS
    - All PASS -> GO
    """
    logger.info("Computing final verdict")

    if not results:
        logger.warning("No checks executed — defaulting to NO-GO")
        return Verdict.NO_GO

    status_counts = Counter(r.status for r in results)

    logger.info(
        f"Check summary: PASS={status_counts.get(CheckStatus.PASS, 0)}, "
        f"WARN={status_counts.get(CheckStatus.WARN, 0)}, "
        f"FAIL={status_counts.get(CheckStatus.FAIL, 0)}"
    )

    if status_counts.get(CheckStatus.ERROR, 0) > 0:
        logger.info("Final verdict: ERROR (Connectivity/Infrastructure issue)")
        return Verdict.ERROR

    if status_counts.get(CheckStatus.FAIL, 0) > 0:
        logger.info("Final verdict: NO-GO")
        return Verdict.NO_GO

    if status_counts.get(CheckStatus.WARN, 0) > 0:
        logger.info("Final verdict: GO WITH WARNINGS")
        return Verdict.GO_WITH_WARNINGS

    logger.info("Final verdict: GO")
    return Verdict.GO


def is_migration_allowed(verdict):
    """
    Check if migration is allowed based on the final verdict.
    """
    return verdict in {Verdict.GO, Verdict.GO_WITH_WARNINGS}
