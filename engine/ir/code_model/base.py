from dataclasses import dataclass, field
from typing import Optional, Dict
import uuid

@dataclass
class SourceLocation:
    file: str
    line_start: int
    line_end: int

@dataclass(kw_only=True)
class IRNode:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    location: Optional[SourceLocation] = None
    metadata: Dict[str, str] = field(default_factory=dict)