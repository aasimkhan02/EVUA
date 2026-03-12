from pipeline.patterns.base import PatternDetector
from pipeline.patterns.roles import SemanticRole
from pipeline.patterns.confidence import Confidence
from pipeline.patterns.result import PatternResult

class SimpleWatchDetector(PatternDetector):
    """
    Detect $scope.$watch / $watchCollection / $watchGroup cases that are
    safe to auto-migrate to RxJS BehaviorSubject.

    Matches controllers that have any of:
      - "shallow"    — $scope.$watch(expr, fn)
      - "collection" — $scope.$watchCollection(expr, fn)
      - "group"      — $scope.$watchGroup([exprs], fn)

    Excludes controllers that ONLY have "deep" watches (those are risky
    and handled by WatcherRiskRule instead).
    """

    # Depths we will auto-migrate
    _SAFE_DEPTHS = {"shallow", "collection", "group"}

    def extract(self, analysis):
        matches = []

        for module in analysis.modules:
            for cls in module.classes:
                watch_depths = set(getattr(cls, "watch_depths", []))
                has_safe = bool(watch_depths & self._SAFE_DEPTHS)
                has_deep = "deep" in watch_depths

                # Only auto-migrate if there is at least one safe watch
                # and NO deep watches on the same controller (deep = risky)
                if has_safe and not has_deep:
                    depth_note = ", ".join(sorted(watch_depths & self._SAFE_DEPTHS))
                    matches.append((
                        cls,
                        SemanticRole.SHALLOW_WATCH,
                        Confidence(0.9, f"Safe $watch detected ({depth_note})")
                    ))

        return matches