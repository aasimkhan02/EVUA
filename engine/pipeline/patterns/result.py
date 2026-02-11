from dataclasses import dataclass
from typing import Dict, List
from ir.code_model.base import IRNode

from .roles import SemanticRole
from .confidence import PatternConfidence


@dataclass
class PatternResult:
    roles_by_node: Dict[str, List[SemanticRole]]        # IRNode.id → roles
    confidence_by_node: Dict[str, PatternConfidence]    # IRNode.id → confidence
