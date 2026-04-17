from abc import ABC, abstractmethod
from .result import IngestionResult

class IngestionStage(ABC):

    @abstractmethod
    def ingest(self) -> IngestionResult:
        pass
