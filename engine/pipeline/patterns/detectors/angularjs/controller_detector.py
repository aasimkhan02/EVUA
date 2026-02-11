from pipeline.patterns.roles import SemanticRole

class ControllerDetector:
    def detect(self, analysis):
        roles = {}
        confidence = {}

        for m in analysis.modules:
            for c in m.classes:
                roles.setdefault(c.id, []).append(SemanticRole.CONTROLLER)
                confidence[c.id] = 0.9

                # Heuristic: name-based (works with your current IR)
                if c.name.lower().endswith("controller"):
                    roles.setdefault(c.id, []).append(SemanticRole.COMPONENT_METHOD)
                    confidence[c.id] = 0.95

        return roles, confidence
