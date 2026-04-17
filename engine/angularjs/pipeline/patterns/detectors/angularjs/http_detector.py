from pipeline.patterns.base import PatternDetector
from pipeline.patterns.roles import SemanticRole
from pipeline.patterns.confidence import Confidence

class HttpDetector(PatternDetector):
    def extract(self, analysis_result):
        matches = []

        for call in getattr(analysis_result, "http_calls", []):
            matches.append((
                call,
                SemanticRole.HTTP_CALL,
                Confidence(0.9, "$http/$q call detected")
            ))

        return matches
