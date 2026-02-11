from dataclasses import dataclass
from enum import Enum
from ..code_model.base import IRNode

class ChangeSource(str, Enum):
    RULE = "rule"
    AI = "ai"
    HUMAN = "human"

@dataclass
class MigrationRecord(IRNode):
    source: ChangeSource
    reason: str
