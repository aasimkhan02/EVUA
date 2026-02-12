from pipeline.risk.levels import RiskLevel

class WatcherRiskRule:
    def assess(self, analysis, patterns, transformation):
        risk_by_change = {}
        reason_by_change = {}

        for change in transformation.changes:
            level = RiskLevel.SAFE
            reason = "No risky watcher behavior detected"

            # Find the matching class for this change (if any)
            matched = None
            for m in analysis.modules:
                for c in m.classes:
                    if c.id == change.before_id:
                        matched = c
                        break
                if matched:
                    break

            if matched is not None:
                scope_writes = getattr(matched, "scope_writes", [])
                watch_depths = getattr(matched, "watch_depths", [])
                uses_compile = getattr(matched, "uses_compile", False)
                has_nested_scopes = getattr(matched, "has_nested_scopes", False)

                # 🚨 Hard edge-cases → MANUAL
                if "deep" in watch_depths:
                    level = RiskLevel.MANUAL
                    reason = "Deep $watch detected (high behavioral coupling risk)"

                elif uses_compile:
                    level = RiskLevel.MANUAL
                    reason = "$compile usage detected (runtime DOM compilation)"

                elif has_nested_scopes:
                    level = RiskLevel.MANUAL
                    reason = "Nested scope inheritance detected (non-trivial migration)"

                # ⚠️ Softer risks
                elif len(scope_writes) >= 3:
                    level = RiskLevel.RISKY
                    reason = "Heavy $scope mutation detected (state coupling risk)"

                elif len(scope_writes) > 0:
                    level = RiskLevel.RISKY
                    reason = "Multiple $scope writes detected"

            risk_by_change[change.id] = level
            reason_by_change[change.id] = reason

        return risk_by_change, reason_by_change
