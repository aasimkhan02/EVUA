"""
RuleApplier
===========

Executes all transformation rules in sequence.

Each rule must implement:

    apply(analysis, patterns) -> List[Change]

Where:
    analysis  = AnalysisResult produced by analyzers
    patterns  = PatternResult produced by pattern detection

Rules are executed in the order they are registered.

Typical rule pipeline:

    rules = [
        ControllerToComponentRule(...),
        ServiceToInjectableRule(...),
        DirectiveToComponentRule(...),
        DirectiveToPipeRule(...),      # <-- our new filter→pipe rule
        HttpToHttpClientRule(...),
        RouteMigratorRule(...),
        SimpleWatchToRxjsRule(...),
        ComponentInteractionRule(...),
        AppModuleUpdaterRule(...),     # MUST run last
    ]

The applier simply executes them and aggregates the Change objects.
"""


class RuleApplier:
    def __init__(self, rules):
        """
        Parameters
        ----------
        rules : list
            Ordered list of transformation rule instances.
        """
        self.rules = rules

    def apply_all(self, analysis, patterns):
        """
        Execute all rules sequentially.

        Parameters
        ----------
        analysis : AnalysisResult
        patterns : PatternResult

        Returns
        -------
        list[Change]
            All changes produced by transformation rules.
        """

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

                if result:
                    all_changes.extend(result)

            except Exception as e:
                print(f"[TRANSFORM] FAILED {rule_name}: {e}")

                import traceback
                traceback.print_exc()

        print(f"[TRANSFORM] Total changes produced: {len(all_changes)}\n")

        return all_changes