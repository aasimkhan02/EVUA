from dataclasses import dataclass
from enum import Enum
from .base import TemplateNode

class BindingType(str, Enum):
    READ = "read"       # {{ user.name }}
    WRITE = "write"     # ng-model, form input
    TWO_WAY = "two_way"

@dataclass
class Binding(TemplateNode):
    expression: str          # symbolic expression only
    target_symbol: str       # IR Symbol ID
    binding_type: BindingType
