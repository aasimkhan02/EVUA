from abc import ABC, abstractmethod
from ..analysis.result import AnalysisResult
from ..patterns.result import PatternResult
from ..transformation.result import TransformationResult
from ..risk.result import RiskResult
from ..ai.result import AIResult
from ..validation.result import ValidationResult
from .result import ReportingResult

class ReportingStage(ABC):

    @abstractmethod
    def report(
        self,
        analysis: AnalysisResult,
        patterns: PatternResult,
        transformation: TransformationResult,
        risk: RiskResult,
        ai: AIResult | None,
        validation: ValidationResult
    ) -> ReportingResult:
        pass
