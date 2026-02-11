from ..risk.levels import RiskLevel

class AIGate:
    def should_invoke(self, risk_level: RiskLevel, confidence: float) -> bool:
        if risk_level == RiskLevel.MANUAL:
            return True
        if risk_level == RiskLevel.RISKY and confidence < 0.7:
            return True
        return False
