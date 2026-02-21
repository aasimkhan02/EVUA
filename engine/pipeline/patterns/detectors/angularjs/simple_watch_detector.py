from pipeline.patterns.base import PatternDetector
from pipeline.patterns.roles import SemanticRole
from pipeline.patterns.confidence import Confidence
from pipeline.patterns.result import PatternResult

class SimpleWatchDetector(PatternDetector):
    """
    Detect shallow $scope.$watch(...) cases that are safe to auto-migrate to RxJS.
    """

    def extract(self, analysis):
        matches = []

        for module in analysis.modules:
            for cls in module.classes:
                watch_depths = getattr(cls, "watch_depths", [])
                if "shallow" in watch_depths and "deep" not in watch_depths:
                    matches.append((
                        cls,
                        SemanticRole.SHALLOW_WATCH,
                        Confidence(0.9, "Shallow $watch detected")
                    ))

        return matches
