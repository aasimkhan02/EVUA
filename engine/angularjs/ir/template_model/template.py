from dataclasses import dataclass, field
from typing import List
from .base import TemplateNode
from .binding import Binding
from .directive import Directive

@dataclass
class Template(TemplateNode):
    bindings: List[Binding] = field(default_factory=list)
    directives: List[Directive] = field(default_factory=list)
