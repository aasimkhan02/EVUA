from pipeline.patterns.base import PatternDetector
from pipeline.patterns.roles import SemanticRole
from pipeline.patterns.confidence import Confidence

class HttpDetector(PatternDetector):
    def detect(self, ir):
        matches = []

        for call in getattr(ir, "http_calls", []):
            if call.method in ("get", "post", "put", "delete"):
                matches.append((call, SemanticRole.HTTP_CALL, Confidence.HIGH))
            elif call.method.startswith("q_"):
                matches.append((call, SemanticRole.PROMISE_CHAIN, Confidence.MEDIUM))

        return matches
