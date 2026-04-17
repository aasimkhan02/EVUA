from dataclasses import dataclass

@dataclass
class ConfidenceScore:
    value: float        # 0.0 → 1.0
    explanation: str
