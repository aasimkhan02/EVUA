from dataclasses import dataclass
from typing import Optional
from .base import IRNode

@dataclass(kw_only=True)
class Symbol(IRNode):
    name: str
    type_hint: Optional[str] = None
    mutable: bool = True
