from pipeline.risk.levels import RiskLevel

class TemplateBindingRiskRule:
    def assess(self, analysis, patterns, transformation):
        risk_by_change = {}
        reason_by_change = {}

        for change in transformation.changes:
            if "component_" in change.after_id:
                risk_by_change[change.id] = RiskLevel.RISKY
                reason_by_change[change.id] = "Two-way template bindings increase migration risk"
        return risk_by_change, reason_by_change
