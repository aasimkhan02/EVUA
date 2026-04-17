from dataclasses import dataclass, field
from typing import List
from .base import IRNode
from .function import Function
from .symbol import Symbol

@dataclass(kw_only=True)
class Class(IRNode):
    name: str
    fields: List[Symbol] = field(default_factory=list)
    methods: List[Function] = field(default_factory=list)
