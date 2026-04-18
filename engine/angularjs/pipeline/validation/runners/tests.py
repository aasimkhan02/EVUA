"""
pipeline/validation/runners/tests.py
======================================

Framework-aware test runner for EVUA-generated Angular projects.

Changes in this revision
-------------------------
- Returns a TestResult dataclass instead of a bare (bool, str) tuple.
  The dataclass carries suite-level counts that feed the validation
  summary and — via the report JSON — the UI coverage card.
- Parses Karma / Jasmine output to extract:
    suites_total, suites_passed, suites_failed,
    specs_total,  specs_passed,  specs_failed, specs_skipped
- Falls back to zero-counts on parse failure (the pass/fail bool still
  reflects the real exit code).
- cli.py call-site change required: unpack a TestResult instead of
  (bool, str).  See migration note at the bottom of this file.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class TestResult:
    passed:        bool
    output:        str
    # Spec-level counts (from parsed Karma/Jasmine output)
    specs_total:   int = 0
    specs_passed:  int = 0
    specs_failed:  int = 0
    specs_skipped: int = 0
    # Suite-level counts
    suites_total:  int = 0
    suites_passed: int = 0
    suites_failed: int = 0
    # If the runner itself was unavailable
    runner_missing: bool = False
    timed_out:      bool = False

    @property
    def spec_percent(self) -> int:
        """Percentage of specs that passed (0 when total is 0)."""
        if self.specs_total == 0:
            return 0
        return round(self.specs_passed / self.specs_total * 100)

    @property
    def ratio_label(self) -> str:
        return f"{self.specs_passed} / {self.specs_total}"

    def to_dict(self) -> dict:
        return {
            "passed":         self.passed,
            "specs_total":    self.specs_total,
            "specs_passed":   self.specs_passed,
            "specs_failed":   self.specs_failed,
            "specs_skipped":  self.specs_skipped,
            "spec_percent":   self.spec_percent,
            "ratio_label":    self.ratio_label,
            "suites_total":   self.suites_total,
            "suites_passed":  self.suites_passed,
            "suites_failed":  self.suites_failed,
            "runner_missing": self.runner_missing,
            "timed_out":      self.timed_out,
        }


# ---------------------------------------------------------------------------
# Output parsers
# ---------------------------------------------------------------------------

# Karma summary line patterns — multiple flavours in the wild:
#   "Executed 42 of 42 SUCCESS (0.123 secs / 0.098 secs)"
#   "Executed 40 of 42 (2 FAILED) (0.1 secs)"
#   "SUMMARY: 5 tests, 2 failures"         ← Jasmine 4 standalone
#   "Tests:    passed: 14, failed: 2, skipped: 0, total: 16"  ← Jest

_KARMA_EXEC_RE = re.compile(
    r'Executed\s+(?P<ran>\d+)\s+of\s+(?P<total>\d+)'
    r'(?:\s+\((?P<failed>\d+)\s+FAILED\))?'
    r'(?:\s+(?P<status>SUCCESS|FAILED))?',
    re.IGNORECASE,
)

_JASMINE_SUMMARY_RE = re.compile(
    r'(\d+)\s+test[s]?\s*,\s*(\d+)\s+failure[s]?',
    re.IGNORECASE,
)

_JEST_RE = re.compile(
    r'Tests:\s+(?:passed:\s*(?P<passed>\d+),\s*)?'
    r'(?:failed:\s*(?P<failed>\d+),\s*)?'
    r'(?:skipped:\s*(?P<skipped>\d+),\s*)?'
    r'total:\s*(?P<total>\d+)',
    re.IGNORECASE,
)

_SUITE_RE = re.compile(
    r'Test Suites:\s*'
    r'(?:(?P<failed>\d+)\s+failed,\s*)?'
    r'(?P<passed>\d+)\s+passed,\s*(?P<total>\d+)\s+total',
    re.IGNORECASE,
)


def _parse_test_output(output: str) -> dict:
    """
    Extract spec counts from combined stdout+stderr of a test run.
    Returns a dict with keys matching TestResult fields (excluding
    passed/output/runner_missing/timed_out).
    """
    counts: dict = {
        "specs_total": 0, "specs_passed": 0,
        "specs_failed": 0, "specs_skipped": 0,
        "suites_total": 0, "suites_passed": 0, "suites_failed": 0,
    }

    # Try Jest suite line first (most structured)
    suite_m = _SUITE_RE.search(output)
    if suite_m:
        counts["suites_total"]  = int(suite_m.group("total") or 0)
        counts["suites_passed"] = int(suite_m.group("passed") or 0)
        counts["suites_failed"] = int(suite_m.group("failed") or 0)

    # Jest spec line
    jest_m = _JEST_RE.search(output)
    if jest_m:
        counts["specs_total"]   = int(jest_m.group("total")   or 0)
        counts["specs_passed"]  = int(jest_m.group("passed")  or 0) if jest_m.group("passed")  else 0
        counts["specs_failed"]  = int(jest_m.group("failed")  or 0) if jest_m.group("failed")  else 0
        counts["specs_skipped"] = int(jest_m.group("skipped") or 0) if jest_m.group("skipped") else 0
        if not jest_m.group("passed"):
            counts["specs_passed"] = counts["specs_total"] - counts["specs_failed"] - counts["specs_skipped"]
        return counts

    # Karma "Executed N of M" line
    karma_m = _KARMA_EXEC_RE.search(output)
    if karma_m:
        total  = int(karma_m.group("total")  or 0)
        failed = int(karma_m.group("failed") or 0)
        counts["specs_total"]  = total
        counts["specs_failed"] = failed
        counts["specs_passed"] = total - failed
        return counts

    # Jasmine standalone summary
    jasmine_m = _JASMINE_SUMMARY_RE.search(output)
    if jasmine_m:
        total  = int(jasmine_m.group(1))
        failed = int(jasmine_m.group(2))
        counts["specs_total"]  = total
        counts["specs_failed"] = failed
        counts["specs_passed"] = total - failed
        return counts

    return counts


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

class TestRunner:
    """
    Runs framework-aware tests against the migrated Angular project.

    Priority:
      1. Generated Angular workspace at out/angular-app  (ng test)
      2. Angular workspace at repo_path                  (ng test)
      3. Fallback npm test in repo_path

    Returns a TestResult — never raises.
    """

    def run(self, repo_path: str) -> TestResult:
        repo_path   = Path(repo_path)
        angular_out = Path("out/angular-app")

        try:
            if (angular_out / "angular.json").exists():
                cmd = ["ng", "test", "--watch=false", "--browsers=ChromeHeadless"]
                cwd = angular_out
            elif (repo_path / "angular.json").exists():
                cmd = ["ng", "test", "--watch=false", "--browsers=ChromeHeadless"]
                cwd = repo_path
            else:
                cmd = ["npm", "test", "--", "--watch=false"]
                cwd = repo_path

            result = subprocess.run(
                cmd,
                cwd=str(cwd),
                capture_output=True,
                text=True,
                timeout=180,
            )

            passed = result.returncode == 0
            output = result.stdout + "\n" + result.stderr
            counts = _parse_test_output(output)

            return TestResult(passed=passed, output=output, **counts)

        except FileNotFoundError as exc:
            msg = f"Test command not found: {exc}"
            return TestResult(
                passed=False,
                output=msg,
                runner_missing=True,
            )
        except subprocess.TimeoutExpired:
            return TestResult(
                passed=False,
                output="Test execution timed out",
                timed_out=True,
            )
        except Exception as exc:
            return TestResult(passed=False, output=str(exc))


# ---------------------------------------------------------------------------
# cli.py migration note
# ---------------------------------------------------------------------------
# Before (old signature):
#   tests_passed, _ = TestRunner().run(str(repo_path))
#
# After (new):
#   test_result = TestRunner().run(str(repo_path))
#   tests_passed = test_result.passed
#   # store test_result.to_dict() in validation_summary["test_run"]