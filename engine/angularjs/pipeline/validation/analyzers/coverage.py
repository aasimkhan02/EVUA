"""
pipeline/validation/analyzers/coverage.py
==========================================

Measures test-coverage completeness of the generated Angular project by
inspecting which migratable source files have a companion .spec.ts.

What "coverage" means here
--------------------------
After migration, every generated .component.ts / .service.ts / .pipe.ts /
.directive.ts should have a .spec.ts alongside it.  Angular CLI scaffolds
these automatically, but EVUA's rule-appliers sometimes skip the spec or the
spec is present only as a stub (zero `it(` blocks).

This analyzer counts:
  - covered   : source file has a .spec.ts with at least one `it(` or `test(`
  - stub       : source file has a .spec.ts but no test bodies (empty scaffold)
  - uncovered  : source file has no .spec.ts at all

The ratio `covered / total` is the number that feeds the UI "TEST COVERAGE"
card.  stub files count as uncovered in the percentage but are reported
separately so the UI can show a more nuanced breakdown.

Usage
-----
    from pipeline.validation.analyzers.coverage import CoverageAnalyzer

    result = CoverageAnalyzer(project_root).analyze()
    # result.percent          → int  (0-100)
    # result.covered          → int
    # result.stub             → int
    # result.uncovered        → int
    # result.total            → int
    # result.ratio_label      → str  e.g. "14 / 18"
    # result.by_type          → dict  e.g. {"component": {...}, "service": {...}}
    # result.uncovered_files  → list of relative path strings
    # result.stub_files       → list of relative path strings
    # result.to_dict()        → JSON-serialisable summary
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List


# ---------------------------------------------------------------------------
# Source-file types we care about
# ---------------------------------------------------------------------------

# Maps the Angular suffix to the human label used in by_type
_SUFFIX_TO_TYPE: dict[str, str] = {
    ".component.ts": "component",
    ".service.ts":   "service",
    ".pipe.ts":      "pipe",
    ".directive.ts": "directive",
    ".guard.ts":     "guard",
    ".resolver.ts":  "resolver",
}

# Spec stem ends in one of these (Angular convention)
_SPEC_SUFFIXES: tuple[str, ...] = (
    ".spec.ts",
)

# A spec file contains at least one real test body when it has these patterns
_TEST_BODY_RE = re.compile(r'\bit\s*\(|test\s*\(', re.MULTILINE)

# Files to always ignore (module root, routing, barrel files)
_IGNORE_NAMES = frozenset({
    "app.module.ts",
    "app-routing.module.ts",
    "app.component.ts",   # scaffolded by Angular CLI, not a migrated entity
    "main.ts",
    "polyfills.ts",
    "environments",
})


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class TypeCoverageStats:
    total:     int = 0
    covered:   int = 0
    stub:      int = 0
    uncovered: int = 0

    @property
    def percent(self) -> int:
        if self.total == 0:
            return 0
        return round(self.covered / self.total * 100)


@dataclass
class CoverageResult:
    """Full coverage analysis of a generated Angular project."""
    covered:         int
    stub:            int
    uncovered:       int
    total:           int
    by_type:         Dict[str, TypeCoverageStats]
    uncovered_files: List[str] = field(default_factory=list)
    stub_files:      List[str] = field(default_factory=list)
    covered_files:   List[str] = field(default_factory=list)

    @property
    def percent(self) -> int:
        if self.total == 0:
            return 0
        return round(self.covered / self.total * 100)

    @property
    def ratio_label(self) -> str:
        return f"{self.covered} / {self.total}"

    def to_dict(self) -> dict:
        return {
            "percent":         self.percent,
            "covered":         self.covered,
            "stub":            self.stub,
            "uncovered":       self.uncovered,
            "total":           self.total,
            "ratio_label":     self.ratio_label,
            "uncovered_files": self.uncovered_files,
            "stub_files":      self.stub_files,
            "by_type": {
                t: {
                    "total":     s.total,
                    "covered":   s.covered,
                    "stub":      s.stub,
                    "uncovered": s.uncovered,
                    "percent":   s.percent,
                }
                for t, s in self.by_type.items()
            },
        }


# ---------------------------------------------------------------------------
# Analyzer
# ---------------------------------------------------------------------------

class CoverageAnalyzer:
    """
    Walk a generated Angular project and measure spec-file coverage.

    Parameters
    ----------
    project_root : Path
        The root of the Angular workspace (contains angular.json).
        The analyzer looks inside src/app/ by default, but falls back
        to walking the entire project_root if src/app/ is absent.
    """

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)

    # ── Public ────────────────────────────────────────────────────────────

    def analyze(self) -> CoverageResult:
        """
        Scan the generated project and return a CoverageResult.
        Never raises — returns a zero-coverage result on any error.
        """
        try:
            return self._analyze()
        except Exception as exc:
            print(f"  [coverage] Analysis failed: {exc}")
            return CoverageResult(
                covered=0, stub=0, uncovered=0, total=0,
                by_type={},
            )

    # ── Private ───────────────────────────────────────────────────────────

    def _analyze(self) -> CoverageResult:
        src_dir = self.project_root / "src" / "app"
        if not src_dir.exists():
            # Fallback: walk from project root
            src_dir = self.project_root

        # Collect all .spec.ts paths keyed by their stem without .spec
        # e.g.  "user.component.spec.ts"  →  key "user.component"
        spec_map: dict[str, Path] = {}
        for spec_file in src_dir.rglob("*.spec.ts"):
            # stem without ".spec" suffix
            stem = spec_file.name[: -len(".spec.ts")]
            spec_map[stem] = spec_file

        by_type: dict[str, TypeCoverageStats] = {}
        covered_files:   list[str] = []
        stub_files:      list[str] = []
        uncovered_files: list[str] = []

        for source_file in sorted(src_dir.rglob("*.ts")):
            if source_file.name.endswith(".spec.ts"):
                continue  # skip spec files themselves

            # Determine which Angular type this file is
            angular_type = self._classify(source_file)
            if angular_type is None:
                continue  # not a migratable entity

            if any(ig in source_file.parts for ig in _IGNORE_NAMES):
                continue

            rel = str(source_file.relative_to(self.project_root))

            # Key used to look up the spec
            stem = self._source_stem(source_file)
            spec_path = spec_map.get(stem)

            stats = by_type.setdefault(angular_type, TypeCoverageStats())
            stats.total += 1

            if spec_path is None:
                stats.uncovered += 1
                uncovered_files.append(rel)
            else:
                spec_text = spec_path.read_text(encoding="utf-8", errors="replace")
                if _TEST_BODY_RE.search(spec_text):
                    stats.covered += 1
                    covered_files.append(rel)
                else:
                    stats.stub += 1
                    stub_files.append(rel)

        total     = sum(s.total     for s in by_type.values())
        covered   = sum(s.covered   for s in by_type.values())
        stub      = sum(s.stub      for s in by_type.values())
        uncovered = sum(s.uncovered for s in by_type.values())

        result = CoverageResult(
            covered=covered,
            stub=stub,
            uncovered=uncovered,
            total=total,
            by_type=by_type,
            covered_files=covered_files,
            stub_files=stub_files,
            uncovered_files=uncovered_files,
        )

        self._print_summary(result)
        return result

    def _classify(self, path: Path) -> str | None:
        """Return the Angular entity type or None if not a migratable file."""
        name = path.name
        for suffix, type_label in _SUFFIX_TO_TYPE.items():
            if name.endswith(suffix):
                return type_label
        return None

    def _source_stem(self, path: Path) -> str:
        """
        Return the stem used to look up the companion spec.
        e.g. user.component.ts  →  "user.component"
        """
        name = path.name
        if name.endswith(".ts"):
            return name[:-3]  # strip ".ts"
        return name

    def _print_summary(self, result: CoverageResult) -> None:
        print(
            f"  [coverage] {result.covered}/{result.total} files covered "
            f"({result.percent}%)  |  {result.stub} stub  "
            f"|  {result.uncovered} uncovered"
        )
        for type_label, stats in sorted(result.by_type.items()):
            print(
                f"  [coverage]   {type_label:<12} "
                f"{stats.covered}/{stats.total}  ({stats.percent}%)"
            )
        if result.uncovered_files:
            print("  [coverage] Files with no spec:")
            for f in result.uncovered_files[:10]:
                print(f"  [coverage]   {f}")
            if len(result.uncovered_files) > 10:
                print(f"  [coverage]   ...({len(result.uncovered_files) - 10} more)")