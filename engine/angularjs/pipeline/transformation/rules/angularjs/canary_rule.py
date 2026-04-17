"""
pipeline/transformation/canary_rule.py

A diagnostic rule you can inject at the front of your rule list
to verify the pipeline is correctly wired before running real rules.

Usage in your pipeline setup:
    from pipeline.transformation.canary_rule import CanaryRule
    rules = [CanaryRule(), ControllerToComponentRule(), ...]
    applier = RuleApplier(rules)

Remove (or set enabled=False) once everything is verified.
"""

from ir.migration_model.change import Change
from ir.migration_model.base import ChangeSource
from pipeline.patterns.roles import SemanticRole


class CanaryRule:
    """
    Emits exactly one Change to confirm the transformation pipeline fires.
    Also prints a detailed diagnostic of what it sees in analysis + patterns.
    """

    def __init__(self, enabled: bool = True):
        self.enabled = enabled

    def apply(self, analysis, patterns):
        if not self.enabled:
            return []

        print("\n========== CanaryRule (pipeline diagnostic) ==========")

        # --- analysis shape ---
        modules = getattr(analysis, "modules", [])
        http_calls = getattr(analysis, "http_calls", [])
        watches = getattr(analysis, "watches", [])
        print(f"  analysis.modules:    {len(modules)}")
        print(f"  analysis.http_calls: {len(http_calls)}")
        print(f"  analysis.watches:    {len(watches)}")

        for m in modules:
            classes = getattr(m, "classes", [])
            print(f"    Module {getattr(m, 'path', '?')} → {len(classes)} class(es)")
            for c in classes:
                print(f"      Class: {c.name} (id={c.id})")

        # --- patterns shape ---
        roles_by_node = getattr(patterns, "roles_by_node", {})
        matched_patterns = getattr(patterns, "matched_patterns", [])
        print(f"  patterns.roles_by_node size:    {len(roles_by_node)}")
        print(f"  patterns.matched_patterns size: {len(matched_patterns)}")

        role_summary: dict = {}
        for node_id, roles in roles_by_node.items():
            for r in roles:
                role_summary[r] = role_summary.get(r, 0) + 1
        for role, count in role_summary.items():
            print(f"    {role}: {count} node(s)")

        print("  ✅ Canary fired — pipeline wiring OK")
        print("========== CanaryRule DONE ==========\n")

        return [
            Change(
                before_id="canary_before",
                after_id="canary_after",
                source=ChangeSource.RULE,
                reason="CanaryRule: pipeline wiring verified"
            )
        ]
