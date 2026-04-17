from dataclasses import dataclass, field
from typing import List, Optional

from .change import Change
from .decision import MigrationDecision
from .confidence import ConfidenceScore


@dataclass
class MigrationSnapshot:
    changes: List[Change] = field(default_factory=list)
    decision: Optional[MigrationDecision] = None
    confidence: Optional[ConfidenceScore] = None
