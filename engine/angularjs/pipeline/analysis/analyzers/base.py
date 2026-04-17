from abc import ABC, abstractmethod
from pathlib import Path
from typing import List

class Analyzer(ABC):
    @abstractmethod
    def analyze(self, paths: List[Path]):
        """
        Return raw artifacts:
        - raw_modules
        - raw_dependencies
        - raw_templates
        - raw_behaviors
        """
        pass
