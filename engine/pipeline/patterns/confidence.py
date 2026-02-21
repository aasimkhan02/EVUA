from dataclasses import dataclass

@dataclass
class PatternConfidence:
    value: float      # 0.0 → 1.0
    explanation: str

Confidence = PatternConfidence
