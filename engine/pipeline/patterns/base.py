from abc import ABC, abstractmethod
from ..analysis.result import AnalysisResult
from .result import PatternResult

class PatternStage(ABC):

    @abstractmethod
    def extract(self, analysis: AnalysisResult) -> PatternResult:
        pass
