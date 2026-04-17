from dataclasses import dataclass, field
from typing import List, Optional
from .base import IRNode
from .symbol import Symbol

@dataclass(kw_only=True)
class Function(IRNode):
    name: str
    parameters: List[Symbol]
    returns: Optional[str] = None
    body_refs: List[str] = field(default_factory=list)
