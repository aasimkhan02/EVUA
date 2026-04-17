from abc import ABC, abstractmethod
from ..ingestion.result import IngestionResult
from .result import AnalysisResult

class AnalysisStage(ABC):

    @abstractmethod
    def analyze(self, ingestion: IngestionResult) -> AnalysisResult:
        pass
