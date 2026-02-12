from pipeline.patterns.roles import SemanticRole

class ControllerDetector:
    def detect(self, analysis):
        roles = {}
        confidence = {}

        for m in analysis.modules:
            for c in m.classes:
                name = c.name.lower()

                # ✅ Real AngularJS controllers only
                if name.endswith("controller"):
                    roles.setdefault(c.id, []).append(SemanticRole.CONTROLLER)
                    confidence[c.id] = max(confidence.get(c.id, 0.0), 0.95)

                    # Heuristic: controllers expose component methods/state
                    roles.setdefault(c.id, []).append(SemanticRole.COMPONENT_METHOD)
                    roles.setdefault(c.id, []).append(SemanticRole.COMPONENT_STATE)
                    confidence[c.id] = max(confidence.get(c.id, 0.0), 0.9)

                # 🚨 Edge-case semantics → tag as unsafe controller patterns
                if getattr(c, "uses_compile", False):
                    roles.setdefault(c.id, []).append(SemanticRole.TEMPLATE_BINDING)
                    confidence[c.id] = max(confidence.get(c.id, 0.0), 0.9)

                if getattr(c, "has_nested_scopes", False):
                    roles.setdefault(c.id, []).append(SemanticRole.TEMPLATE_BINDING)
                    confidence[c.id] = max(confidence.get(c.id, 0.0), 0.9)

                if hasattr(c, "watch_depths") and "deep" in getattr(c, "watch_depths", []):
                    roles.setdefault(c.id, []).append(SemanticRole.COMPONENT_STATE)
                    confidence[c.id] = max(confidence.get(c.id, 0.0), 0.8)

        return roles, confidence
