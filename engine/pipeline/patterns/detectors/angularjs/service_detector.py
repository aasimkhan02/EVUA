from pipeline.patterns.roles import SemanticRole

class ServiceDetector:
    def detect(self, analysis):
        roles = {}
        confidence = {}

        for m in analysis.modules:
            for c in m.classes:
                if c.name.lower().endswith("service"):
                    roles[c.id] = [SemanticRole.SERVICE]
                    confidence[c.id] = 0.9

        return roles, confidence
