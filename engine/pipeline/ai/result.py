from dataclasses import dataclass
from typing import Dict

@dataclass
class AISuggestion:
    change_id: str
    suggested_code: str
    explanation: str
    confidence: float

@dataclass
class AIResult:
    suggestions: Dict[str, AISuggestion]   # change_id → suggestion
