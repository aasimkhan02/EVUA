from dataclasses import dataclass
from enum import Enum
from typing import Optional


class DecisionType(Enum):
    APPROVE = "approve"
    EDIT = "edit"
    REJECT = "reject"


@dataclass
class MigrationDecision:
    change_id: str
    decision: DecisionType
    edited_after_id: Optional[str] = None
    comment: Optional[str] = None
