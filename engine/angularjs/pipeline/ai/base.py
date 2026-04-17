from abc import ABC, abstractmethod
from ..analysis.result import AnalysisResult
from ..patterns.result import PatternResult
from ..transformation.result import TransformationResult
from ..risk.result import RiskResult
from .result import AIResult

class AIStage(ABC):

    @abstractmethod
    def assist(
        self,
        analysis: AnalysisResult,
        patterns: PatternResult,
        transformation: TransformationResult,
        risk: RiskResult
    ) -> AIResult:
        pass
