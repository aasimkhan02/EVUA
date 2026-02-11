from dataclasses import dataclass, field
from typing import List
from .base import IRNode
from .class_ import Class
from .function import Function
from .symbol import Symbol

@dataclass(kw_only=True)
class Module(IRNode):
    name: str
    classes: List[Class] = field(default_factory=list)
    functions: List[Function] = field(default_factory=list)
    globals: List[Symbol] = field(default_factory=list)
