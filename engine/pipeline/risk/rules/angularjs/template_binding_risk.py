from pipeline.risk.levels import RiskLevel
from pipeline.patterns.roles import SemanticRole


class TemplateBindingRiskRule:
    """
    Assesses risk from template bindings detected in HTML.

    Key insight: simple structural bindings (ng-repeat -> *ngFor, ng-if -> *ngIf,
    ng-class -> [ngClass]) are mechanical 1-to-1 migrations. They are NOT risky.
    Only complex combinations — where bidirectional event handling is coupled with
    structural bindings — suggest non-trivial template migration.

    Rule priority: this rule runs before WatcherRiskRule.
    WatcherRiskRule runs last and will override any RISKY set here with its own
    assessment, so false positives from template bindings don't persist.
    """

    def assess(self, analysis, patterns, transformation):
        risk_by_change   = {}
        reason_by_change = {}

        for change in transformation.changes:
            roles = patterns.roles_by_node.get(change.before_id, [])

            has_template_binding = SemanticRole.TEMPLATE_BINDING in roles
            has_event_handler    = SemanticRole.EVENT_HANDLER in roles

            if has_template_binding and has_event_handler:
                # Bidirectional binding + event handling suggests complex
                # two-way data flow that may not map cleanly to Angular.
                # Flag RISKY (not MANUAL — WatcherRiskRule handles hard MANUAL cases).
                risk_by_change[change.id]   = RiskLevel.RISKY
                reason_by_change[change.id] = (
                    "Template has both structural bindings and event handlers "
                    "(verify two-way data flow after migration)"
                )

            else:
                # TEMPLATE_BINDING alone = ng-repeat/ng-if/ng-show etc.
                # These are safe mechanical migrations — do NOT flag as RISKY.
                # EVENT_HANDLER alone = (click) bindings — also straightforward.
                risk_by_change[change.id]   = RiskLevel.SAFE
                reason_by_change[change.id] = "Template bindings are safe mechanical migrations"

        return risk_by_change, reason_by_change