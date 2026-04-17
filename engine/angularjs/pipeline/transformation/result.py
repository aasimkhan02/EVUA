from dataclasses import dataclass, field
from typing import List
from ir.migration_model.change import Change


@dataclass
class TransformationResult:
    changes: List[Change] = field(default_factory=list)
    new_ir_nodes: List[str] = field(default_factory=list)  # IRNode IDs created
