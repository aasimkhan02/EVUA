from dataclasses import dataclass
from typing import Dict
from .metrics import Metrics

@dataclass
class ReportingResult:
    metrics: Metrics
    reports: Dict[str, str]    # format → content (e.g., "markdown" → "...") 
