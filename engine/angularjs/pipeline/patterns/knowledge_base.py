from dataclasses import dataclass
from .roles import SemanticRole

@dataclass
class PatternMapping:
    pattern_name: str
    role: SemanticRole
    confidence_hint: float
    description: str

class PatternKnowledgeBase:
    def __init__(self):
        self._patterns: dict[str, PatternMapping] = {}

    def register(self, mapping: PatternMapping):
        self._patterns[mapping.pattern_name] = mapping

    def get(self, name: str) -> PatternMapping | None:
        return self._patterns.get(name)
