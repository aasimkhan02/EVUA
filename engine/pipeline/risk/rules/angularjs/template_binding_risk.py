from pipeline.risk.levels import RiskLevel
from pipeline.patterns.roles import SemanticRole

class TemplateBindingRiskRule:
    def assess(self, analysis, patterns, transformation):
        risk_by_change = {}
        reason_by_change = {}

        for change in transformation.changes:
            roles = patterns.roles_by_node.get(change.before_id, [])

            if SemanticRole.TEMPLATE_BINDING in roles:
                risk_by_change[change.id] = RiskLevel.MANUAL
                reason_by_change[change.id] = "Template performs two-way bindings to controller state (high coupling risk)"
            else:
                risk_by_change[change.id] = RiskLevel.RISKY
                reason_by_change[change.id] = "Template bindings present (moderate coupling risk)"

        return risk_by_change, reason_by_change
