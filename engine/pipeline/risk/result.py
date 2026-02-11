from dataclasses import dataclass
from typing import Dict
from .levels import RiskLevel

@dataclass
class RiskResult:
    risk_by_change_id: Dict[str, RiskLevel]        # Change.id → RiskLevel
    reason_by_change_id: Dict[str, str]            # Change.id → explanation
