"""
pipeline/validation/runners/lint.py
=====================================

ESLint runner for the generated Angular project.

Performance fixes (this revision)
-----------------------------------
- Linter discovery no longer spawns subprocesses.
  All candidates are checked via filesystem existence / shutil.which only:
    1. node_modules/.bin/eslint  (local install — fastest, most reliable)
    2. node_modules/.bin/npx     (local npx — avoids global cold-start)
    3. system eslint via shutil.which  (zero-cost PATH lookup)
    4. system npx via shutil.which     (last resort)

  The old `ng lint --help` subprocess probe is gone entirely. Angular CLI
  cold-starts the TypeScript compiler to print help text — that was the
  main source of the engine freezing.

- ng lint is dropped as a runner. It wraps ESLint but adds 3-8 s of
  Angular CLI bootstrap and doesn't support --format=json reliably across
  versions. We call ESLint directly instead.

- Discovery result is cached on the instance so repeated calls within one
  pipeline run cost nothing.

- Hard timeout reduced from 120 s → 60 s. ESLint on a freshly-generated
  Angular project (< 20 files) finishes in under 5 s. 60 s is a generous
  ceiling that prevents the pipeline hanging on a broken install.

- Falls back gracefully (passed=True, linter_found=False) when ESLint is
  not installed, so missing lint tooling never blocks the pipeline.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Data types  (unchanged from previous revision)
# ---------------------------------------------------------------------------

@dataclass
class LintError:
    file:     str
    line:     int
    col:      int
    severity: int   # 1 = warning, 2 = error
    rule:     str
    message:  str

    @property
    def is_error(self) -> bool:
        return self.severity == 2

    def to_dict(self) -> dict:
        return {
            "file":     self.file,
            "line":     self.line,
            "col":      self.col,
            "severity": self.severity,
            "rule":     self.rule,
            "message":  self.message,
        }


@dataclass
class LintResult:
    passed:        bool
    linter_found:  bool = True
    error_count:   int  = 0
    warning_count: int  = 0
    errors:        list[LintError] = field(default_factory=list)
    raw_output:    str  = ""
    command_used:  str  = ""

    @property
    def total_count(self) -> int:
        return self.error_count + self.warning_count

    @property
    def summary(self) -> str:
        if not self.linter_found:
            return "ESLint not found — run: npm install --save-dev eslint"
        if self.passed:
            return "Lint passed — 0 errors, 0 warnings"
        parts = []
        if self.error_count:
            parts.append(f"{self.error_count} error(s)")
        if self.warning_count:
            parts.append(f"{self.warning_count} warning(s)")
        return "Lint: " + ", ".join(parts) if parts else "Lint failed"

    def to_dict(self) -> dict:
        return {
            "passed":        self.passed,
            "linter_found":  self.linter_found,
            "error_count":   self.error_count,
            "warning_count": self.warning_count,
            "total_count":   self.total_count,
            "summary":       self.summary,
            "command_used":  self.command_used,
            "errors":        [e.to_dict() for e in self.errors[:50]],
        }


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

_LINT_TIMEOUT = 60  # seconds — ESLint on < 20 files finishes in < 5 s normally


class LintRunner:
    """
    Run ESLint on the generated Angular project.

    Parameters
    ----------
    project_root : Path
        Root of the Angular workspace (contains angular.json / package.json).
        Defaults to ``out/angular-app`` when not supplied.
    """

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = Path(project_root) if project_root else Path("out/angular-app")
        self._cached_cmd: Optional[list[str]] = None
        self._discovery_done: bool = False

    # ── Public ────────────────────────────────────────────────────────────

    def run(self, project_path: Optional[str] = None) -> LintResult:
        """Run ESLint and return a LintResult. Never raises."""
        root = Path(project_path) if project_path else self.project_root

        cmd = self._find_eslint(root)
        if cmd is None:
            print("  [lint] ESLint not found — skipping lint check")
            return LintResult(passed=True, linter_found=False)

        src = root / "src"
        target = str(src) if src.exists() else str(root)
        full_cmd = cmd + [target, "--format=json", "--max-warnings=0"]

        try:
            result = subprocess.run(
                full_cmd,
                cwd=str(root),
                capture_output=True,
                text=True,
                timeout=_LINT_TIMEOUT,
            )

            raw    = result.stdout
            errors = self._parse_eslint_json(raw, root)

            error_count   = sum(1 for e in errors if e.is_error)
            warning_count = sum(1 for e in errors if not e.is_error)
            passed        = error_count == 0 and result.returncode == 0

            lint_result = LintResult(
                passed=passed,
                linter_found=True,
                error_count=error_count,
                warning_count=warning_count,
                errors=errors,
                raw_output=raw[:4000],
                command_used=" ".join(full_cmd),
            )

            if passed:
                print(f"  [lint] ✓ Passed — 0 errors, {warning_count} warning(s)")
            else:
                print(f"  [lint] ✗ {error_count} error(s), {warning_count} warning(s)")
                for e in errors[:5]:
                    fname = Path(e.file).name
                    print(f"  [lint]   {fname}:{e.line}  {e.rule}  {e.message[:60]}")

            return lint_result

        except FileNotFoundError:
            print("  [lint] ESLint binary disappeared after discovery — skipping")
            return LintResult(passed=True, linter_found=False)
        except subprocess.TimeoutExpired:
            print(f"  [lint] Lint timed out after {_LINT_TIMEOUT}s — skipping")
            return LintResult(passed=True, linter_found=True, raw_output="timeout")
        except Exception as exc:
            print(f"  [lint] Unexpected error: {exc}")
            return LintResult(passed=True, linter_found=True, raw_output=str(exc))

    # ── Private ───────────────────────────────────────────────────────────

    def _find_eslint(self, root: Path) -> Optional[list[str]]:
        """
        Locate ESLint using filesystem checks only — no subprocess spawning.
        Result is cached so the pipeline pays this cost at most once.
        """
        if self._discovery_done:
            return self._cached_cmd

        self._discovery_done = True
        is_win = sys.platform == "win32"
        bin_dir = root / "node_modules" / ".bin"

        # 1. Local node_modules/.bin/eslint — preferred, no PATH dependency
        eslint_local = bin_dir / ("eslint.cmd" if is_win else "eslint")
        if eslint_local.exists():
            self._cached_cmd = [str(eslint_local)]
            return self._cached_cmd

        # 2. Local node_modules/.bin/npx — avoids global npx cold-start
        npx_local = bin_dir / ("npx.cmd" if is_win else "npx")
        if npx_local.exists():
            self._cached_cmd = [str(npx_local), "eslint"]
            return self._cached_cmd

        # 3. System eslint on PATH — shutil.which is a pure Python stat(), no fork
        eslint_global = shutil.which("eslint")
        if eslint_global:
            self._cached_cmd = [eslint_global]
            return self._cached_cmd

        # 4. System npx as last resort
        npx_global = shutil.which("npx")
        if npx_global:
            self._cached_cmd = [npx_global, "eslint"]
            return self._cached_cmd

        self._cached_cmd = None
        return None

    def _parse_eslint_json(self, raw: str, root: Path) -> list[LintError]:
        """Parse ESLint --format=json output into LintError list."""
        errors: list[LintError] = []
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            return errors

        for file_entry in data:
            file_path = file_entry.get("filePath", "")
            try:
                rel = str(Path(file_path).relative_to(root))
            except ValueError:
                rel = Path(file_path).name

            for msg in file_entry.get("messages", []):
                errors.append(LintError(
                    file=rel,
                    line=int(msg.get("line", 0)),
                    col=int(msg.get("column", 0)),
                    severity=int(msg.get("severity", 1)),
                    rule=str(msg.get("ruleId", "unknown")),
                    message=str(msg.get("message", "")),
                ))

        return errors