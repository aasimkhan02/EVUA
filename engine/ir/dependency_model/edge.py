from dataclasses import dataclass, field
from .base import DependencyType, DependencyMetadata

@dataclass
class DependencyEdge:
    source_id: str         
    target_id: str          
    type: DependencyType
    metadata: DependencyMetadata = field(default_factory=DependencyMetadata)
