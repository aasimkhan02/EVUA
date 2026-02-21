from pipeline.risk.levels import RiskLevel

# Threshold for "heavy" scope mutation to be considered RISKY.
# Only applies when there is NO watch at all.
# Set high (7) because normal controllers legitimately write many scope properties.
_HEAVY_SCOPE_WRITE_THRESHOLD = 7

# Threshold for shallow-watch + heavy mutation.
# Shallow watch + writes is safe (BehaviorSubject handles it), so only flag
# RISKY if the mutation count is extreme.
_SHALLOW_WATCH_HEAVY_THRESHOLD = 10


class WatcherRiskRule:
    def assess(self, analysis, patterns, transformation):
        risk_by_change   = {}
        reason_by_change = {}

        # Build fast lookup: class.id -> class object
        class_by_id = {}
        for m in analysis.modules:
            for c in m.classes:
                class_by_id[c.id] = c

        for change in transformation.changes:
            level  = RiskLevel.SAFE
            reason = "No risky watcher behavior detected"

            # ── $q.defer / $q.all changes ──────────────────────────────────
            # HttpToHttpClientRule embeds "q_defer" in the reason string.
            # Manual Promise->Observable migration required regardless of class signals.
            change_reason = getattr(change, "reason", "") or ""
            if "q_defer" in change_reason:
                risk_by_change[change.id]   = RiskLevel.MANUAL
                reason_by_change[change.id] = (
                    "$q.defer() detected — Promise chain requires manual RxJS migration"
                )
                continue

            # ── Look up the IR class that owns this change ─────────────────
            matched = class_by_id.get(change.before_id)

            if matched is not None:
                scope_writes      = getattr(matched, "scope_writes", [])
                watch_depths      = getattr(matched, "watch_depths", [])
                uses_compile      = getattr(matched, "uses_compile", False)
                has_nested_scopes = getattr(matched, "has_nested_scopes", False)

                unique_writes = len(set(scope_writes))

                # ── Hard MANUAL signals ────────────────────────────────────
                if "deep" in watch_depths:
                    level  = RiskLevel.MANUAL
                    reason = "Deep $watch detected (high behavioral coupling risk)"

                elif uses_compile:
                    level  = RiskLevel.MANUAL
                    reason = "$compile usage detected (runtime DOM compilation)"

                elif has_nested_scopes:
                    level  = RiskLevel.MANUAL
                    reason = "Nested scope inheritance detected (non-trivial migration)"

                # ── Shallow $watch ─────────────────────────────────────────
                # BehaviorSubject rewrite is well-understood and safe.
                # Only flag RISKY if scope mutation is extreme (threshold 10).
                elif "shallow" in watch_depths:
                    if unique_writes >= _SHALLOW_WATCH_HEAVY_THRESHOLD:
                        level  = RiskLevel.RISKY
                        reason = (
                            f"Shallow $watch with extreme $scope mutation "
                            f"({unique_writes} unique writes)"
                        )
                    else:
                        level  = RiskLevel.SAFE
                        reason = "Shallow $watch → safe RxJS BehaviorSubject rewrite"

                # ── No watch — only flag RISKY for genuinely heavy mutation ─
                # Normal controllers write several scope properties (users, loading,
                # selectedItem etc). That alone is not a migration risk.
                # Only flag when mutation count is unusually high (threshold 7).
                elif unique_writes >= _HEAVY_SCOPE_WRITE_THRESHOLD:
                    level  = RiskLevel.RISKY
                    reason = (
                        f"Heavy $scope mutation without reactive pattern "
                        f"({unique_writes} unique writes — consider refactoring to store)"
                    )

                # else: unique_writes < threshold, no watch → SAFE (default)

            # Always write an explicit result so WatcherRiskRule's SAFE
            # overrides any earlier RISKY written by TemplateBindingRiskRule
            # for the same change.id (WatcherRiskRule runs last).
            risk_by_change[change.id]   = level
            reason_by_change[change.id] = reason

        return risk_by_change, reason_by_change