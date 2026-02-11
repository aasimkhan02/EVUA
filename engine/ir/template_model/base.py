from dataclasses import dataclass
from typing import Optional
from ..code_model.base import IRNode

@dataclass(kw_only=True)
class TemplateNode(IRNode):
    name: Optional[str] = None   # element / block identifier
