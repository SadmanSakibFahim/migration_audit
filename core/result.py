from dataclasses import dataclass
from typing import Optional, Dict
from core.enums import CheckStatus

@dataclass
class TestResult:
    name: str
    status: CheckStatus
    message: str
    details: Optional[Dict] = None
    metrics: Optional[Dict[str, float]] = None