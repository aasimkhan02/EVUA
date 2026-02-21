from pathlib import Path

BENCHMARKS_ROOT = Path("benchmarks/angularjs")
REPORTS_ROOT = Path("reports")

# Regression thresholds (fail CI if exceeded)
MAX_COVERAGE_DROP = 0.05
MAX_PRECISION_DROP = 0.03

SUPPORTED_ROLES = ["SAFE", "RISKY", "MANUAL"]
