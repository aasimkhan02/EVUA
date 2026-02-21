from pipeline.risk.levels import RiskLevel


class ServiceRiskRule:
    """
    First-pass risk rule for service and HTTP migration changes.

    This rule runs FIRST (before TemplateBindingRiskRule and WatcherRiskRule).
    It sets a baseline SAFE for the changes it recognises. Later rules override
    where needed. The goal is to ensure HTTP call changes and service migrations
    don't get accidentally flagged RISKY by TemplateBindingRiskRule (which may
    see a TEMPLATE_BINDING role on those nodes).

    Covered cases:
      - ServiceToInjectableRule changes  → always SAFE
      - HttpToHttpClientRule changes     → SAFE unless $q.defer (handled by WatcherRiskRule)
      - ControllerToComponentRule        → SAFE baseline (WatcherRiskRule overrides if needed)
      - SimpleWatchToRxjsRule            → SAFE baseline
    """

    # Reason substrings that identify change types by their written reason string
    _SERVICE_MARKERS  = ("service", "injectable", "@injectable")
    _HTTP_MARKERS     = ("$http", "httpclient", "http.get", "http.post",
                         "http.put", "http.delete", "migrated into")
    _CONTROLLER_MARKERS = ("component", "written to", "routing")
    _WATCH_MARKERS    = ("behaviorsubject", "rxjs", "$watch")

    def assess(self, analysis, patterns, transformation):
        risk_by_change   = {}
        reason_by_change = {}

        for change in transformation.changes:
            reason_lower = (getattr(change, "reason", "") or "").lower()

            # q_defer is handled by WatcherRiskRule — skip here
            if "q_defer" in reason_lower:
                continue

            # Every change gets a SAFE baseline from this rule.
            # WatcherRiskRule (which runs last) overrides with RISKY/MANUAL
            # only when it finds a specific behavioural signal.
            risk_by_change[change.id]   = RiskLevel.SAFE
            reason_by_change[change.id] = "Baseline safe — no structural migration risk detected"

            # Refine the reason string based on change type for readability
            if any(m in reason_lower for m in self._SERVICE_MARKERS):
                reason_by_change[change.id] = "Service maps cleanly to @Injectable()"

            elif any(m in reason_lower for m in self._HTTP_MARKERS):
                reason_by_change[change.id] = "$http → HttpClient is a safe deterministic migration"

            elif any(m in reason_lower for m in self._WATCH_MARKERS):
                reason_by_change[change.id] = "BehaviorSubject rewrite is safe"

            elif any(m in reason_lower for m in self._CONTROLLER_MARKERS):
                reason_by_change[change.id] = "Controller scaffold is safe — WatcherRiskRule will refine"

        return risk_by_change, reason_by_change