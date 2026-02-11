from pathlib import Path
from typing import List
from .base import Analyzer

class JavaAnalyzer(Analyzer):
    def analyze(self, paths: List[Path]):
        return [], [], [], []
