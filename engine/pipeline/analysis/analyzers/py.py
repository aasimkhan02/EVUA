from pathlib import Path
from typing import List
from .base import Analyzer

class PyAnalyzer(Analyzer):
    def analyze(self, paths: List[Path]):
        return [], [], [], []
