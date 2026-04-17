from dataclasses import dataclass
from enum import Enum
from .base import Behavior

class BindingSemantics(str, Enum):
    ONE_WAY = "one_way"
    TWO_WAY = "two_way"
    IMPLICIT = "implicit"

@dataclass
class RuntimeBinding(Behavior):
    source_symbol_id: str
    target_symbol_id: str
    semantics: BindingSemantics
