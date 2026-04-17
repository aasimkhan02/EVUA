from abc import ABC, abstractmethod
from ..analysis.result import AnalysisResult
from ..patterns.result import PatternResult
from .result import TransformationResult

class TransformationStage(ABC):

    @abstractmethod
    def transform(
        self,
        analysis: AnalysisResult,
        patterns: PatternResult
    ) -> TransformationResult:
        pass
