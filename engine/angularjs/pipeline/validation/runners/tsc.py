"""
pipeline/validation/runners/tsc.py
===================================

TypeScript compilation validator for EVUA-generated Angular projects.

Runs `tsc --noEmit` on the generated project after the transformation rules
have written their output. This is the key paper metric: "does the engine
produce code that actually compiles?"

Behaviour
---------
- Discovers tsconfig automatically (tsconfig.app.json > tsconfig.json)
- Tries `tsc` first, then `npx tsc` as fallback (covers global vs local installs)
- Parses TypeScript error output into structured TscError objects
- Returns a TscResult with pass/fail + categorised error list
- Never raises — always returns a result, even if tsc is not installed

Error categories (for report grouping)
---------------------------------------
  structural   — TS2304 (cannot find name), TS2339 (no property), TS2345 (arg type)
  missing_import — TS2307 (cannot find module)
  strict       — TS2564 (not initialized), TS2531 (possibly null)
  template     — errors in .html files (Angular template compilation)
  other        — everything else

Usage
-----
    from pipeline.validation.runners.tsc import TscValidator

    validator = TscValidator(project_root)
    result    = validator.run()

    if result.passed:
        print("✓ TypeScript compilation passed")
    else:
        print(f"✗ {result.error_count} error(s)")
        for err in result.errors[:5]:
            print(f"  {err.file}:{err.line}  {err.code}  {err.message}")
"""

import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# Data types
# ─────────────────────────────────────────────────────────────────────────────

# TS error code → category
_CATEGORY_MAP = {
    "TS2304": "structural",     # Cannot find name 'X'
    "TS2339": "structural",     # Property 'X' does not exist
    "TS2345": "structural",     # Argument of type X not assignable
    "TS2322": "structural",     # Type X is not assignable to type Y
    "TS2307": "missing_import", # Cannot find module 'X'
    "TS2306": "missing_import", # File 'X' is not a module
    "TS2564": "strict",         # Property has no initializer (strictPropertyInitialization)
    "TS2531": "strict",         # Object is possibly 'null'
    "TS2532": "strict",         # Object is possibly 'undefined'
    "TS7006": "strict",         # Parameter implicitly has an 'any' type
    "TS7034": "strict",         # Variable implicitly has type 'any'
}

_TEMPLATE_FILE_PATTERN = re.compile(r'\.html$', re.IGNORECASE)

# tsc error line format:
#   path/to/file.ts(10,5): error TS2304: Cannot find name 'foo'.
_ERROR_RE = re.compile(
    r'^(?P<file>.+?)\((?P<line>\d+),(?P<col>\d+)\):\s+error\s+(?P<code>TS\d+):\s+(?P<message>.+)$'
)


@dataclass
class TscError:
    file:     str
    line:     int
    col:      int
    code:     str
    message:  str
    category: str  # structural | missing_import | strict | template | other

    def to_dict(self) -> dict:
        return {
            "file":     self.file,
            "line":     self.line,
            "col":      self.col,
            "code":     self.code,
            "message":  self.message,
            "category": self.category,
        }


@dataclass
class TscResult:
    passed:       bool
    tsc_found:    bool                    # False if tsc / npx not available
    tsconfig:     Optional[str]           # path used, or None if not found
    errors:       list[TscError] = field(default_factory=list)
    raw_output:   str = ""                # full tsc stdout for debugging
    tsc_command:  str = ""                # which command was used

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def errors_by_category(self) -> dict[str, list[TscError]]:
        cats: dict[str, list[TscError]] = {}
        for err in self.errors:
            cats.setdefault(err.category, []).append(err)
        return cats

    @property
    def error_summary(self) -> str:
        if self.passed:
            return "TypeScript compilation passed — 0 errors"
        if not self.tsc_found:
            return "tsc not found — install Node.js and run: npm install -g typescript"
        if not self.tsconfig:
            return "tsconfig.json not found in generated project"
        cats = self.errors_by_category
        parts = [f"{len(v)} {k}" for k, v in sorted(cats.items())]
        return f"{self.error_count} error(s): {', '.join(parts)}"

    def to_dict(self) -> dict:
        return {
            "passed":       self.passed,
            "tsc_found":    self.tsc_found,
            "tsconfig":     self.tsconfig,
            "error_count":  self.error_count,
            "error_summary": self.error_summary,
            "tsc_command":  self.tsc_command,
            "errors_by_category": {
                cat: [e.to_dict() for e in errs]
                for cat, errs in self.errors_by_category.items()
            },
            "errors": [e.to_dict() for e in self.errors],
        }


# ─────────────────────────────────────────────────────────────────────────────
# Validator
# ─────────────────────────────────────────────────────────────────────────────

class TscValidator:
    """
    Runs `tsc --noEmit` on the generated Angular project.

    Parameters
    ----------
    project_root : Path
        Root of the generated Angular project (the directory containing
        tsconfig.json / tsconfig.app.json). Typically:
            out/angular-app/angular-app/
    """

    # tsconfig candidates in preference order
    _TSCONFIG_CANDIDATES = [
        "tsconfig.app.json",
        "tsconfig.json",
    ]

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)

    # ── Public ────────────────────────────────────────────────────────────

    def run(self) -> TscResult:
        """
        Run tsc --noEmit and return a TscResult.
        Never raises. Always returns a result.
        """
        # Ensure node_modules exists — run npm install if missing (idempotent).
        # This is required before tsc can resolve @angular/* imports.
        self._ensure_npm_install()

        tsconfig = self._find_tsconfig()
        if tsconfig is None:
            print(f"  [tsc] tsconfig not found in {self.project_root}")
            return TscResult(
                passed=False,
                tsc_found=True,
                tsconfig=None,
            )

        tsc_cmd = self._find_tsc()
        if tsc_cmd is None:
            print("  [tsc] tsc not found. Install: npm install -g typescript")
            print("  [tsc] Or run:  npm install  inside the generated project")
            print("  [tsc] then:    npx tsc --noEmit")
            return TscResult(
                passed=False,
                tsc_found=False,
                tsconfig=str(tsconfig),
            )

        print(f"  [tsc] Running: {' '.join(tsc_cmd)} --noEmit --project {tsconfig.name}")
        print(f"  [tsc] Working dir: {self.project_root}")

        try:
            proc = subprocess.run(
                tsc_cmd + ["--noEmit", "--project", str(tsconfig)],
                capture_output=True,
                text=True,
                cwd=str(self.project_root),
                timeout=120,  # 2 min max — large projects can be slow
            )
        except subprocess.TimeoutExpired:
            print("  [tsc] TIMEOUT after 120s")
            return TscResult(
                passed=False,
                tsc_found=True,
                tsconfig=str(tsconfig),
                raw_output="TIMEOUT",
                tsc_command=" ".join(tsc_cmd),
            )
        except Exception as e:
            print(f"  [tsc] ERROR: {e}")
            return TscResult(
                passed=False,
                tsc_found=True,
                tsconfig=str(tsconfig),
                raw_output=str(e),
                tsc_command=" ".join(tsc_cmd),
            )

        raw = proc.stdout + proc.stderr
        errors = self._parse_errors(raw)
        passed = proc.returncode == 0 and len(errors) == 0

        result = TscResult(
            passed=passed,
            tsc_found=True,
            tsconfig=str(tsconfig),
            errors=errors,
            raw_output=raw,
            tsc_command=" ".join(tsc_cmd),
        )

        # Print summary
        if passed:
            print("  [tsc] ✓ Compilation passed — 0 errors")
        else:
            print(f"  [tsc] ✗ {result.error_count} error(s)")
            cats = result.errors_by_category
            for cat, errs in sorted(cats.items()):
                print(f"  [tsc]   {cat:15s} {len(errs):3d} error(s)")
            # Print first 10 errors for immediate diagnosis
            print("  [tsc] First errors:")
            for err in errors[:10]:
                # Make path relative for readability
                try:
                    rel = Path(err.file).relative_to(self.project_root)
                except ValueError:
                    rel = Path(err.file).name
                print(f"  [tsc]   {str(rel):<50s} {err.code}  {err.message[:60]}")
            if len(errors) > 10:
                print(f"  [tsc]   ... ({len(errors) - 10} more errors)")

        return result

    # ── Private ───────────────────────────────────────────────────────────

    def _find_tsconfig(self) -> Optional[Path]:
        """Return the first tsconfig file found in project_root."""
        for name in self._TSCONFIG_CANDIDATES:
            candidate = self.project_root / name
            if candidate.exists():
                return candidate
        return None

    def _ensure_npm_install(self) -> None:
        """
        Ensure node_modules is present for tsc to resolve @angular/* imports.

        Strategy: maintain a persistent shared node_modules cache keyed by the
        hash of package.json. On first run with a given package.json, run
        npm install once into the cache. On subsequent runs, create a junction
        (Windows) or symlink (Unix) from <project_root>/node_modules to the
        cached copy — takes milliseconds instead of 3-5 minutes.

        Cache location: <project_root>/../../.evua_node_cache/<hash>/node_modules
        (two levels up from the tmp Angular project puts us inside out/)
        """
        import hashlib
        import os

        node_modules = self.project_root / "node_modules"
        if node_modules.exists():
            return  # already present (real install or symlink/junction)

        pkg_json = self.project_root / "package.json"
        if not pkg_json.exists():
            print("  [tsc] package.json not found — skipping npm install")
            return

        # ── Compute cache key from package.json content ──────────────────
        pkg_content = pkg_json.read_bytes()
        pkg_hash    = hashlib.md5(pkg_content).hexdigest()[:12]

        # Cache root: two dirs up from the Angular project root, so it survives
        # across tmp-dir rotations.  e.g. out/.evua_node_cache/<hash>/node_modules
        cache_root   = self.project_root.parent.parent / ".evua_node_cache"
        cache_nm_dir = cache_root / pkg_hash / "node_modules"

        npm_name = "npm.cmd" if sys.platform == "win32" else "npm"

        # ── If cache miss, install once into a stable location ───────────
        if not cache_nm_dir.exists():
            print(f"  [tsc] node_modules cache miss (key={pkg_hash}) — running npm install once")
            print(f"  [tsc] This takes ~30-60s on first run; subsequent runs will be instant.")
            install_dir = cache_nm_dir.parent
            install_dir.mkdir(parents=True, exist_ok=True)
            # Copy package.json into install dir so npm install works there
            import shutil
            shutil.copy2(pkg_json, install_dir / "package.json")
            try:
                result = subprocess.run(
                    [npm_name, "install"],
                    capture_output=True, text=True,
                    cwd=str(install_dir),
                    timeout=360,
                )
                if result.returncode == 0:
                    print(f"  [tsc] npm install completed — cached at {cache_nm_dir}")
                else:
                    print(f"  [tsc] npm install failed (rc={result.returncode})")
                    if result.stderr:
                        for line in result.stderr.splitlines()[:5]:
                            print(f"  [tsc]   {line}")
                    return
            except FileNotFoundError:
                print("  [tsc] npm not found — install Node.js from https://nodejs.org")
                return
            except subprocess.TimeoutExpired:
                print("  [tsc] npm install timed out after 6 minutes")
                return
        else:
            print(f"  [tsc] node_modules cache hit (key={pkg_hash}) — linking instantly")

        # ── Link cache into the tmp project dir ──────────────────────────
        if not cache_nm_dir.exists():
            print("  [tsc] Cache dir missing after install — falling back to local npm install")
            self._npm_install_local(npm_name, pkg_json)
            return

        try:
            if sys.platform == "win32":
                # Windows: use directory junction (no admin rights needed, unlike symlinks)
                import subprocess as _sp
                _sp.run(
                    ["cmd", "/c", "mklink", "/J",
                     str(node_modules), str(cache_nm_dir)],
                    check=True, capture_output=True,
                )
            else:
                # Unix: symlink
                node_modules.symlink_to(cache_nm_dir)
            print(f"  [tsc] Linked node_modules from cache ({cache_nm_dir.parent.name})")
        except Exception as e:
            print(f"  [tsc] Could not create junction/symlink ({e}) — falling back to copy")
            # Last resort: copy (slow but always works)
            import shutil
            shutil.copytree(str(cache_nm_dir), str(node_modules))

    def _npm_install_local(self, npm_name: str, pkg_json: Path) -> None:
        """Fallback: plain npm install in project_root."""
        print(f"  [tsc] Falling back to local npm install in {self.project_root}")
        try:
            result = subprocess.run(
                [npm_name, "install"],
                capture_output=True, text=True,
                cwd=str(self.project_root),
                timeout=360,
            )
            if result.returncode == 0:
                print("  [tsc] npm install completed successfully")
            else:
                print(f"  [tsc] npm install failed (rc={result.returncode})")
        except FileNotFoundError:
            print("  [tsc] npm not found — install Node.js from https://nodejs.org")
        except subprocess.TimeoutExpired:
            print("  [tsc] npm install timed out")

    def _find_tsc(self) -> Optional[list[str]]:
        """
        Return the tsc command as a list, trying:
          1. tsc (global install)
          2. npx tsc (local / npx)
          3. node_modules/.bin/tsc (local without npx)
        Returns None if nothing works.
        """
        # Windows: tsc.cmd
        tsc_name = "tsc.cmd" if sys.platform == "win32" else "tsc"

        # 1. Global tsc
        try:
            result = subprocess.run(
                [tsc_name, "--version"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                return [tsc_name]
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        # 2. Local via npx
        npx_name = "npx.cmd" if sys.platform == "win32" else "npx"
        try:
            result = subprocess.run(
                [npx_name, "tsc", "--version"],
                capture_output=True, text=True, timeout=15,
                cwd=str(self.project_root),
            )
            if result.returncode == 0:
                return [npx_name, "tsc"]
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        # 3. node_modules/.bin/tsc
        local_tsc = self.project_root / "node_modules" / ".bin" / "tsc"
        if local_tsc.exists():
            return [str(local_tsc)]

        return None

    def _parse_errors(self, output: str) -> list[TscError]:
        """Parse tsc output into TscError objects."""
        errors = []
        for line in output.splitlines():
            m = _ERROR_RE.match(line.strip())
            if not m:
                continue
            code = m.group("code")
            file = m.group("file")
            cat = _CATEGORY_MAP.get(code, "other")
            if _TEMPLATE_FILE_PATTERN.search(file):
                cat = "template"
            errors.append(TscError(
                file=file,
                line=int(m.group("line")),
                col=int(m.group("col")),
                code=code,
                message=m.group("message"),
                category=cat,
            ))
        return errors