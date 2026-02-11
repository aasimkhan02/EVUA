from dataclasses import dataclass
from typing import Dict, List

@dataclass
class ValidationResult:
    passed: bool
    checks: Dict[str, bool]        # check_name → pass/fail
    failures: List[str]           # human-readable reasons
