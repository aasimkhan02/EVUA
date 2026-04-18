"""
pipeline/validation/result.py
==============================

ValidationResult is the single data object that the validation phase writes
and the reporting / frontend layers read.

Fields added in this revision
------------------------------
coverage_report : dict
    Serialised CoverageResult.to_dict().  Contains:
      percent        – int 0-100   (the number the UI card shows)
      covered        – int         (files with at least one real `it(` test)
      stub           – int         (files with a .spec.ts but no test bodies)
      uncovered      – int         (files with no .spec.ts at all)
      total          – int
      ratio_label    – str  e.g. "14 / 18"
      uncovered_files – list[str]
      stub_files      – list[str]
      by_type         – dict  per Angular entity type (component/service/pipe…)

    Empty dict `{}` when coverage analysis was skipped (dry-run) or failed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class ValidationResult:
    passed:   bool
    checks:   Dict[str, bool]   # check_name → pass/fail
    failures: List[str]         # human-readable failure reasons

    # ── new: real spec-file coverage ──────────────────────────────────────
    coverage_report: Dict = field(default_factory=dict)
    """
    Populated by CoverageAnalyzer after the Angular project is written.
    Empty dict when validation ran in dry-run mode or coverage analysis
    was skipped/failed.
    """