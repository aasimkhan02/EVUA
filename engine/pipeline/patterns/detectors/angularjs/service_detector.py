from pipeline.patterns.base import PatternDetector
from pipeline.patterns.roles import SemanticRole
from pipeline.patterns.confidence import Confidence


class ServiceDetector(PatternDetector):
    def extract(self, analysis):
        matches = []

        for m in analysis.modules:
            for c in m.classes:
                if c.name.lower().endswith("service"):
                    matches.append((
                        c,
                        SemanticRole.SERVICE,
                        Confidence(0.9, "Service detected")
                    ))

        return matches
