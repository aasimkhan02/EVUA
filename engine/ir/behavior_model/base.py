from dataclasses import dataclass
from ..code_model.base import IRNode

@dataclass
class Behavior(IRNode):
    description: str
