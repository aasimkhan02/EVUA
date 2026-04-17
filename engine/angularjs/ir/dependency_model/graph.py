from dataclasses import dataclass, field
from typing import List
from .edge import DependencyEdge

@dataclass
class DependencyGraph:
    edges: List[DependencyEdge] = field(default_factory=list)

    def add_edge(self, edge: DependencyEdge):
        self.edges.append(edge)

    def outgoing(self, source_id: str) -> List[DependencyEdge]:
        return [e for e in self.edges if e.source_id == source_id]

    def incoming(self, target_id: str) -> List[DependencyEdge]:
        return [e for e in self.edges if e.target_id == target_id]

    def depends_on(self, source_id: str, target_id: str) -> bool:
        return any(
            e.source_id == source_id and e.target_id == target_id
            for e in self.edges
        )
