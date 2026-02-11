from dataclasses import dataclass
from enum import Enum
from .base import TemplateNode

class DirectiveType(str, Enum):
    LOOP = "loop"             # ng-repeat, for
    CONDITIONAL = "if"        # ng-if, if
    EVENT = "event"           # ng-click, onClick

@dataclass
class Directive(TemplateNode):
    directive_type: DirectiveType
    expression: str           # condition, iterable, handler
