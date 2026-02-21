from pipeline.risk.levels import RiskLevel
from pipeline.patterns.roles import SemanticRole

class TemplateBindingRiskRule:
    def assess(self, analysis, patterns, transformation):
        risk_by_change = {}
        reason_by_change = {}

        for change in transformation.changes:
            roles = patterns.roles_by_node.get(change.before_id, [])

            # Directives / transclusion / structural bindings → MANUAL
            if SemanticRole.TEMPLATE_BINDING in roles and SemanticRole.EVENT_HANDLER in roles:
                risk_by_change[change.id] = RiskLevel.MANUAL
                reason_by_change[change.id] = (
                    "Template uses complex bindings/events (directives/transclusion detected)"
                )

            # Template bindings present → RISKY
            elif SemanticRole.TEMPLATE_BINDING in roles:
                risk_by_change[change.id] = RiskLevel.RISKY
                reason_by_change[change.id] = "Template bindings present (moderate coupling risk)"

            else:
                risk_by_change[change.id] = RiskLevel.SAFE
                reason_by_change[change.id] = "No risky template bindings detected"

        return risk_by_change, reason_by_change
