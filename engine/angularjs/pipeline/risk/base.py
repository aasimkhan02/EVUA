from abc import ABC, abstractmethod
from ..analysis.result import AnalysisResult
from ..patterns.result import PatternResult
from ..transformation.result import TransformationResult
from .result import RiskResult

class RiskStage(ABC):

    @abstractmethod
    def assess(
        self,
        analysis: AnalysisResult,
        patterns: PatternResult,
        transformation: TransformationResult
    ) -> RiskResult:
        pass
