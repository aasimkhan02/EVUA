from dataclasses import dataclass
from enum import Enum
from typing import Optional

class DependencyType(str, Enum):
    IMPORT = "import"
    CALL = "call"
    INJECT = "inject"
    EXTENDS = "extends"
    IMPLEMENTS = "implements"
    TEMPLATE_BINDING = "template_binding"

@dataclass
class DependencyMetadata:
    optional: bool = False
    runtime_only: bool = False
    notes: Optional[str] = None
