from pipeline.patterns.base import PatternDetector
from pipeline.patterns.roles import SemanticRole
from pipeline.patterns.confidence import Confidence
from pipeline.patterns.result import PatternResult


class TemplateBindingDetector(PatternDetector):

    def detect(self, analysis):
        """
        Primary API used by the pipeline orchestrator.
        Returns (roles_by_node dict, confidence dict) directly.
        """
        roles = {}
        confidence = {}

        for t in analysis.templates:
            for d in getattr(t, "directives", []):
                roles.setdefault(d.id, []).append(SemanticRole.EVENT_HANDLER)
                confidence[d.id] = max(confidence.get(d.id, 0.0), 0.8)

                if getattr(d, "directive_type", None) is not None:
                    roles.setdefault(d.id, []).append(SemanticRole.TEMPLATE_BINDING)
                    confidence[d.id] = max(confidence.get(d.id, 0.0), 0.85)

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

    def extract(self, analysis):
        """
        Required by PatternStage ABC.
        Returns a proper PatternResult — roles_by_node dict, confidence_by_node dict.
        Previously returned PatternResult(list) which silently corrupted roles_by_node.
        """
        roles, conf_floats = self.detect(analysis)

        confidence_by_node = {
            node_id: Confidence(conf_floats.get(node_id, 0.5), "Template binding detected")
            for node_id in roles
        }

        return PatternResult(
            roles_by_node=roles,
            confidence_by_node=confidence_by_node,
        )