from pipeline.patterns.roles import SemanticRole

class TemplateBindingDetector:
    def detect(self, analysis):
        roles = {}
        confidence = {}

        # Template-level bindings (ng-if/ng-repeat/ng-click etc.)
        for t in analysis.templates:
            for d in getattr(t, "directives", []):
                roles.setdefault(d.id, []).append(SemanticRole.EVENT_HANDLER)
                confidence[d.id] = max(confidence.get(d.id, 0.0), 0.8)

                # Structural/template directives
                if getattr(d, "directive_type", None) is not None:
                    roles.setdefault(d.id, []).append(SemanticRole.TEMPLATE_BINDING)
                    confidence[d.id] = max(confidence.get(d.id, 0.0), 0.85)

        # JS-level directives detected by analyzer (compile/link/transclusion)
        for d in getattr(analysis, "directives", []):
            roles.setdefault(d.id, []).append(SemanticRole.TEMPLATE_BINDING)
            confidence[d.id] = max(confidence.get(d.id, 0.0), 0.95)

            if getattr(d, "has_compile", False) or getattr(d, "has_link", False):
                roles.setdefault(d.id, []).append(SemanticRole.TEMPLATE_BINDING)
                confidence[d.id] = max(confidence.get(d.id, 0.0), 0.98)

            if getattr(d, "transclude", False):
                roles.setdefault(d.id, []).append(SemanticRole.TEMPLATE_BINDING)
                confidence[d.id] = max(confidence.get(d.id, 0.0), 0.98)

        return roles, confidence
