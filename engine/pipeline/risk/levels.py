from enum import Enum

class RiskLevel(str, Enum):
    SAFE = "safe"
    RISKY = "risky"
    MANUAL = "manual"
