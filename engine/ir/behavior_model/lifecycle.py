from dataclasses import dataclass
from enum import Enum
from .base import Behavior

class LifecyclePhase(str, Enum):
    INIT = "init"
    UPDATE = "update"
    DESTROY = "destroy"

@dataclass
class LifecycleHook(Behavior):
    phase: LifecyclePhase
    owner_id: str              # component / class IRNode ID
