from pipeline.patterns.base import PatternDetector
from pipeline.patterns.roles import SemanticRole
from pipeline.patterns.confidence import Confidence
from pipeline.patterns.result import PatternResult


class ControllerDetector(PatternDetector):

    def detect(self, analysis):
        """
        Primary API used by the pipeline orchestrator.
        Returns (roles_by_node dict, confidence dict) directly.
        """
        roles = {}
        confidence = {}

        for m in analysis.modules:
            for c in m.classes:
                name = c.name.lower()

                if name.endswith("controller") or name.endswith("ctrl"):
                    roles.setdefault(c.id, []).append(SemanticRole.CONTROLLER)
                    roles.setdefault(c.id, []).append(SemanticRole.COMPONENT_METHOD)
                    roles.setdefault(c.id, []).append(SemanticRole.COMPONENT_STATE)
                    confidence[c.id] = max(confidence.get(c.id, 0.0), 0.95)

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

    def extract(self, analysis):
        """
        Required by PatternStage ABC.
        Returns a proper PatternResult — roles_by_node dict, confidence_by_node dict.
        Previously returned PatternResult(list) which silently corrupted roles_by_node.
        """
        roles, conf_floats = self.detect(analysis)

        confidence_by_node = {
            node_id: Confidence(conf_floats.get(node_id, 0.5), "Controller pattern detected")
            for node_id in roles
        }

        return PatternResult(
            roles_by_node=roles,
            confidence_by_node=confidence_by_node,
        )