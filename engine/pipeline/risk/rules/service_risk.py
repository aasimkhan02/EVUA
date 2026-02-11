from pipeline.risk.levels import RiskLevel

class ServiceRiskRule:
    def assess(self, analysis, patterns, transformation):
        risk_by_change = {}
        reason_by_change = {}

        for change in transformation.changes:
            if change.reason.startswith("Service"):
                risk_by_change[change.id] = RiskLevel.SAFE
                reason_by_change[change.id] = "Services map cleanly to @Injectable()"
        return risk_by_change, reason_by_change
