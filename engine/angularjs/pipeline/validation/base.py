from abc import ABC, abstractmethod
from ..analysis.result import AnalysisResult
from ..transformation.result import TransformationResult
from ..ai.result import AIResult
from .result import ValidationResult

class ValidationStage(ABC):

    @abstractmethod
    def validate(
        self,
        analysis: AnalysisResult,
        transformation: TransformationResult,
        ai: AIResult | None
    ) -> ValidationResult:
        pass
