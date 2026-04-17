from dataclasses import dataclass
from .base import Behavior

@dataclass
class Observer(Behavior):
    observed_symbol_id: str    # IR Symbol ID
    trigger: str               # change, deep_change, digest_cycle
