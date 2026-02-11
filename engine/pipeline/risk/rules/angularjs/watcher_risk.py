from pipeline.risk.levels import RiskLevel

class WatcherRiskRule:
    def assess(self, analysis, patterns, transformation):
        risk_by_change = {}
        reason_by_change = {}

        for change in transformation.changes:
            # Default: controllers → components are risky
            level = RiskLevel.RISKY
            reason = "Controller → Component is a semantic paradigm shift"

            # Tighten risk if two-way bindings or many $scope writes exist
            for m in analysis.modules:
                for c in m.classes:
                    if c.id == change.before_id:
                        # Heuristic flags from AST step (Step 1)
                        scope_writes = getattr(c, "scope_writes", [])
                        if scope_writes and len(scope_writes) > 1:
                            level = RiskLevel.MANUAL
                            reason = "Multiple $scope writes detected (two-way binding risk)"

            risk_by_change[change.id] = level
            reason_by_change[change.id] = reason

        return risk_by_change, reason_by_change
