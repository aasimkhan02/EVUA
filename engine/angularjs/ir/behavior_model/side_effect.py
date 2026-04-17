from dataclasses import dataclass
from .base import Behavior

@dataclass
class SideEffect(Behavior):
    cause: str                 # watcher, lifecycle, event
    affected_symbol_id: str