from pipeline.risk.levels import RiskLevel

class WatcherRiskRule:
    def assess(self, analysis, patterns, transformation):
        risk_by_change = {}
        reason_by_change = {}

        for change in transformation.changes:
            level = RiskLevel.RISKY
            reason = "Controller → Component is a semantic paradigm shift"

            for m in analysis.modules:
                for c in m.classes:
                    if c.id == change.before_id:
                        scope_writes = getattr(c, "scope_writes", [])
                        watch_depths = getattr(c, "watch_depths", [])

                        if "deep" in watch_depths:
                            level = RiskLevel.MANUAL
                            reason = "Deep $watch detected (high behavioral coupling risk)"

                        elif len(scope_writes) > 1:
                            level = RiskLevel.RISKY
                            reason = "Multiple $scope writes detected"

                        elif len(scope_writes) >= 3:
                            level = RiskLevel.MANUAL
                            reason = "Heavy $scope mutation detected (state coupling risk)"



                        elif len(scope_writes) > 0:
                            level = RiskLevel.RISKY
                            reason = "Multiple $scope writes detected"

            risk_by_change[change.id] = level
            reason_by_change[change.id] = reason

        return risk_by_change, reason_by_change
