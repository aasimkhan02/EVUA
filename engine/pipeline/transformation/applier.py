class RuleApplier:
    def __init__(self, rules):
        self.rules = rules

    def apply_all(self, analysis, patterns):
        print(f"\n[TRANSFORM] RuleApplier.apply_all() -- {len(self.rules)} rules registered")
        print(f"[TRANSFORM] patterns.roles_by_node size: {len(getattr(patterns, 'roles_by_node', {}))}")
        print(f"[TRANSFORM] analysis.modules count: {len(getattr(analysis, 'modules', []))}")
        print(f"[TRANSFORM] analysis.http_calls count: {len(getattr(analysis, 'http_calls', []))}")

        all_changes = []
        for rule in self.rules:
            rule_name = rule.__class__.__name__
            try:
                result = rule.apply(analysis, patterns)
                count = len(result) if result else 0
                print(f"[TRANSFORM] {rule_name} -> {count} change(s)")
                all_changes.extend(result or [])
            except Exception as e:
                print(f"[TRANSFORM] FAILED {rule_name}: {e}")
                import traceback
                traceback.print_exc()

        print(f"[TRANSFORM] Total changes produced: {len(all_changes)}\n")
        return all_changes