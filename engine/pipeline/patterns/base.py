from abc import ABC, abstractmethod
from ..analysis.result import AnalysisResult
from .result import PatternResult

class PatternStage(ABC):
    @abstractmethod
    def extract(self, analysis: AnalysisResult):
        """
        Implementations may return:
        - PatternResult
        - or List[Tuple[node_or_id, SemanticRole, PatternConfidence]]
        """
        pass

class PatternDetector(PatternStage):
    def detect(self, analysis: AnalysisResult):
        out = self.extract(analysis)

        # Case 1: already normalized
        if isinstance(out, PatternResult):
            return out.roles_by_node, out.confidence_by_node

        # Case 2: list of (node_or_id, role, confidence)
        roles = {}
        confidence = {}

        for node_or_id, role, conf in out:
            node_id = getattr(node_or_id, "id", node_or_id)
            roles.setdefault(node_id, []).append(role)
            confidence[node_id] = conf

        return roles, confidence
