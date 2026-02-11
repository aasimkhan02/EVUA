from dataclasses import dataclass, field
from typing import List
from .change import Change
from .decision import Decision
from .confidence import ConfidenceScore

@dataclass
class MigrationSnapshot:
    changes: List[Change] = field(default_factory=list)
    decision: Decision | None = None
    confidence: ConfidenceScore | None = None
