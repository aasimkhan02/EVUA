from pipeline.patterns.roles import SemanticRole

class TemplateBindingDetector:
    def detect(self, analysis):
        roles = {}
        confidence = {}

        for t in analysis.templates:
            for d in getattr(t, "directives", []):
                roles.setdefault(d.id, []).append(SemanticRole.EVENT_HANDLER)
                confidence[d.id] = 0.8

        return roles, confidence
