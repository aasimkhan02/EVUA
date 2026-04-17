import sys
import io

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


class _FilteredWriter:
    """
    Wraps stdout and drops lines that match known internal debug prefixes.
    Keeps all user-facing output, removes implementation noise.
    """
    _SUPPRESS = (
        "[js.py]",
        "[js.py CHAIN]",
        "[js.py DEBUG]",
        "[js.py .component()]",
        "[svc DEBUG]",
        "[TRANSFORM]",
        "[Scaffold]",
        "[helpers]",
        "========== ",
        "[ControllerToComponent DEBUG]",
        "[ControllerToComponent] DI for",
        "[ControllerToComponent] Template for",
        "[ControllerToComponent] Template written:",
        "[ControllerToComponent] Declared then-body",
        "[ControllerToComponent] Emitting sanitized",
        "[ControllerToComponent] Skipping HTTP-inferred",
        "[ServiceToInjectable] DI for",
        "[ServiceToInjectable] Methods for",
        "[ServiceToInjectable] Detected $resource",
        "[RouteMigrator] Router type",
        "[RouteMigrator] Routes detected",
        "[RouteMigrator]   ngRoute",
        "[HttpToHttpClient] HttpClientModule added",
        "[SimpleWatchToRxjs]  No shallow",
        "[ComponentInteraction] No template",
        "[ComponentInteraction] Relationships",
        "[DirectiveToComponent] No directives",
        "[DirectiveToPipe] Filters detected",
        "[ConstantsAndRun] Constants detected",
        "[ConstantsAndRun] Run blocks detected",
        "[AppModuleUpdater] Found:",
        "[AppModuleUpdater] FormsModule needed",
        "[AppModuleUpdater] HttpClientModule needed",
        "[AppModuleUpdater] Built-in pipes",
        "[AppModuleUpdater]",
    )

    def __init__(self, wrapped):
        self._wrapped = wrapped
        self._buf = ""

    def write(self, text):
        # Buffer until newline so we can check complete lines
        self._buf += text
        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            if not any(line.lstrip().startswith(p) for p in self._SUPPRESS):
                self._wrapped.write(line + "\n")

    def flush(self):
        if self._buf:
            if not any(self._buf.lstrip().startswith(p) for p in self._SUPPRESS):
                self._wrapped.write(self._buf)
            self._buf = ""
        self._wrapped.flush()

    def __getattr__(self, name):
        return getattr(self._wrapped, name)


# Install filtered writer — keeps all user output, drops internal debug noise
sys.stdout = _FilteredWriter(sys.stdout)


from pathlib import Path
import argparse
import json
import re
import difflib
import tempfile
import shutil

from pipeline.ingestion.scanner import FileScanner
from pipeline.ingestion.classifier import FileClassifier, FileType
from pipeline.analysis.dispatcher import AnalyzerDispatcher
from pipeline.analysis.result import AnalysisResult

from pipeline.patterns.detectors.angularjs.controller_detector import ControllerDetector
from pipeline.patterns.detectors.angularjs.http_detector import HttpDetector
from pipeline.patterns.detectors.angularjs.simple_watch_detector import SimpleWatchDetector
from pipeline.patterns.detectors.angularjs.service_detector import ServiceDetector
from pipeline.patterns.detectors.angularjs.directive_detector import DirectiveDetector
from pipeline.patterns.result import PatternResult

from pipeline.transformation.rules.angularjs.controller_to_component import ControllerToComponentRule
from pipeline.transformation.rules.angularjs.http_to_httpclient import HttpToHttpClientRule
from pipeline.transformation.rules.angularjs.simple_watch_to_rxjs import SimpleWatchToRxjsRule
from pipeline.transformation.rules.angularjs.service_to_injectable import ServiceToInjectableRule
from pipeline.transformation.rules.angularjs.route_migrator import RouteMigratorRule
from pipeline.transformation.rules.angularjs.app_module_updater import AppModuleUpdaterRule
from pipeline.transformation.rules.angularjs.component_interaction import ComponentInteractionRule
from pipeline.transformation.applier import RuleApplier
from pipeline.transformation.result import TransformationResult
from pipeline.transformation.rules.angularjs.directive_to_component import DirectiveToComponentRule
from pipeline.transformation.rules.angularjs.directive_to_pipe import DirectiveToPipeRule
from pipeline.transformation.rules.angularjs.constants_and_run import ConstantsAndRunRule

from pipeline.risk.rules.angularjs.watcher_risk import WatcherRiskRule
from pipeline.risk.rules.angularjs.template_binding_risk import TemplateBindingRiskRule
from pipeline.risk.rules.angularjs.directive_risk import DirectiveRiskRule
from pipeline.risk.rules.service_risk import ServiceRiskRule
from pipeline.risk.result import RiskResult
from pipeline.risk.levels import RiskLevel

from pipeline.reporting.reporters.json_reporter import JSONReporter
from pipeline.reporting.reporters.markdown_reporter import MarkdownReporter

from pipeline.validation.runners.tests import TestRunner
from pipeline.validation.comparators.snapshot import SnapshotComparator

from orchestration.pipeline_runner import PipelineRunner
from pipeline.ai.client import AIClient
from pipeline.ai.stage import AIAssistStage
from pipeline.validation.runners.tsc import TscValidator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_snapshots(repo_path: Path):
    for snap_dir in [
        repo_path / "snapshots",
        repo_path.parent / "snapshots",
        repo_path / "repo" / "snapshots",
    ]:
        b, a = snap_dir / "before.json", snap_dir / "after.json"
        if b.exists() or a.exists():
            return b, a
    return repo_path / "snapshots" / "before.json", repo_path / "snapshots" / "after.json"


def _build_id_to_name(analysis) -> dict:
    m = {}
    for module in analysis.modules:
        for cls in module.classes:
            m[cls.id] = cls.name
    return m


def _build_directive_id_to_name(analysis) -> dict:
    m = {}
    for d in getattr(analysis, "directives", []) or []:
        m[d.id] = d.name
    return m


def _resolve_name(change, id_to_name: dict, directive_id_to_name: dict, analysis) -> str:
    name = id_to_name.get(change.before_id)
    if name:
        return name
    name = directive_id_to_name.get(change.before_id)
    if name:
        return name
    for call in getattr(analysis, "http_calls", []):
        if getattr(call, "id", None) == change.before_id:
            owner = getattr(call, "owner_controller", None)
            if owner:
                return owner
    return "unknown"


def _extract_generated_file(reason: str) -> str | None:
    if not reason:
        return None
    raw = None
    for marker in ("written to ", "migrated into "):
        if marker in reason:
            raw = reason.split(marker, 1)[-1].strip()
            break
    if not raw:
        return None
    raw = re.sub(r'\s*\(.*\)\s*$', '', raw).strip()
    fname = Path(raw).name
    if re.match(r'^[\w.-]+\.(ts|html|js|css|json)$', fname):
        return fname
    return None


def _unified_diff(before_text: str, after_text: str, filename: str) -> str:
    """Return a unified diff string between before and after content."""
    before_lines = before_text.splitlines(keepends=True)
    after_lines  = after_text.splitlines(keepends=True)
    diff = difflib.unified_diff(
        before_lines,
        after_lines,
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
        lineterm="",
    )
    return "".join(diff)


def _collect_diffs(out_dir: Path, shadow_dir: Path) -> list[dict]:
    """
    Compare every file in shadow_dir (what would be written) against
    the current state in out_dir (what exists or empty string).
    Returns list of {file, diff, is_new} dicts.
    """
    diffs = []
    for shadow_file in sorted(shadow_dir.rglob("*")):
        if not shadow_file.is_file():
            continue
        rel = shadow_file.relative_to(shadow_dir)
        real_file = out_dir / rel

        after_text  = shadow_file.read_text(encoding="utf-8", errors="replace")
        before_text = real_file.read_text(encoding="utf-8", errors="replace") if real_file.exists() else ""

        if before_text == after_text:
            continue  # no change

        diff = _unified_diff(before_text, after_text, str(rel))
        diffs.append({
            "file":   str(rel),
            "diff":   diff,
            "is_new": not real_file.exists(),
        })
    return diffs


# ---------------------------------------------------------------------------
# Helpers (continued)
# ---------------------------------------------------------------------------

def _rewrite_md_report(repo_path, analysis, patterns, transformation, risk,
                       validation_summary, tsc_result=None):
    """Re-render the markdown report, optionally with tsc section appended."""
    md = MarkdownReporter().render(analysis, patterns, transformation, risk, validation_summary)
    if tsc_result is not None:
        md += "\n\n## TypeScript Compilation\n"
        if tsc_result.passed:
            md += "\n✓ **Compilation passed** — 0 errors\n"
        elif not tsc_result.tsc_found:
            md += "\n⚠ **tsc not found** — install Node.js and TypeScript\n"
            md += "\n```bash\nnpm install -g typescript\n```\n"
        elif not tsc_result.tsconfig:
            md += "\n⚠ **tsconfig.json not found** in generated project\n"
        else:
            md += f"\n✗ **{tsc_result.error_count} error(s)**\n\n"
            for cat, errs in sorted(tsc_result.errors_by_category.items()):
                md += f"### {cat.replace('_', ' ').title()} ({len(errs)})\n"
                for e in errs[:5]:
                    fname = Path(e.file).name
                    md += f"- `{fname}:{e.line}` — {e.code}: {e.message}\n"
                if len(errs) > 5:
                    md += f"- *...{len(errs)-5} more*\n"
    md_path = repo_path / ".evua_report.md"
    md_path.write_text(md, encoding="utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def run_pipeline(
    repo_path: str,
    out_root: Path | str = "out",
    dry_run: bool = False,
    show_diff: bool = False,
    only: list[str] | None = None,
    batch: bool = False,
    ai_assist: bool = False,
    skip_tsc: bool = False,
) -> bool:
    repo_path = Path(repo_path).resolve()
    out_root = Path(out_root).resolve()
    real_out_dir = out_root / "angular-app"

    print(f"\n{'='*60}")
    print(f"Running migration pipeline on: {repo_path}")
    if dry_run:
        print("  MODE: DRY RUN — no files will be written")
    if show_diff:
        print("  MODE: DIFF — showing unified diffs")
    if only:
        print(f"  FILTER: only={only}")
    if skip_tsc:
        print("  MODE: --skip-tsc — TypeScript validation disabled")
    print(f"{'='*60}")

    # In diff mode we write to a temp shadow directory, then compare
    shadow_dir = None
    effective_out_dir = real_out_dir

    if show_diff or dry_run:
        shadow_dir = Path(tempfile.mkdtemp(prefix="evua_shadow_"))
        effective_out_dir = shadow_dir / "angular-app"

    scanner    = FileScanner()
    files      = scanner.scan(str(repo_path))
    classifier = FileClassifier()

    files_by_type = {
        FileType.JS:   [p for p in files if classifier.classify(p) == FileType.JS],
        FileType.HTML: [p for p in files if classifier.classify(p) == FileType.HTML],
        FileType.PY:   [p for p in files if classifier.classify(p) == FileType.PY],
        FileType.JAVA: [p for p in files if classifier.classify(p) == FileType.JAVA],
    }
    n_js = len(files_by_type[FileType.JS])
    print(f"  Ingestion : {len(files)} files  ({n_js} JS)")

    dispatcher = AnalyzerDispatcher()
    analysis: AnalysisResult = dispatcher.dispatch(files_by_type)
    n_classes    = sum(len(m.classes) for m in analysis.modules)
    n_http       = len(analysis.http_calls)
    n_directives = len(getattr(analysis, "directives", []) or [])
    n_routes     = len(getattr(analysis, "routes", []) or [])
    print(f"  Analysis  : {n_classes} classes, {n_http} http calls, {n_directives} directives, {n_routes} routes")

    id_to_name           = _build_id_to_name(analysis)
    directive_id_to_name = _build_directive_id_to_name(analysis)

    roles:      dict = {}
    confidence: dict = {}

    for detector in [
        ControllerDetector(),
        HttpDetector(),
        SimpleWatchDetector(),
        ServiceDetector(),
        DirectiveDetector(),
    ]:
        r, c = detector.detect(analysis)
        for k, v in r.items():
            roles.setdefault(k, []).extend(v)
        confidence.update(c)

    patterns = PatternResult(roles_by_node=roles, confidence_by_node=confidence)
    print(f"  Patterns  : {len(roles)} nodes matched")

    # Build rule list — respect --only filter
    # RouteMigratorRule runs FIRST — it owns app-routing.module.ts entirely.
    # ControllerToComponentRule no longer touches routing.
    _all_rules = {
        "routing":      RouteMigratorRule(out_dir=effective_out_dir, dry_run=dry_run),
        "controllers":  ControllerToComponentRule(out_dir=effective_out_dir, dry_run=dry_run),
        "services":     ServiceToInjectableRule(out_dir=effective_out_dir, dry_run=dry_run),
        "http":         HttpToHttpClientRule(out_dir=effective_out_dir, dry_run=dry_run),
        "watch":        SimpleWatchToRxjsRule(out_dir=effective_out_dir, dry_run=dry_run),
        "interaction":  ComponentInteractionRule(out_dir=effective_out_dir, dry_run=dry_run),
        "directives_component": DirectiveToComponentRule(out_dir=effective_out_dir, dry_run=dry_run),
        "directives_pipe": DirectiveToPipeRule(out_dir=effective_out_dir, dry_run=dry_run),
        "constants":    ConstantsAndRunRule(out_dir=effective_out_dir, dry_run=dry_run),
        "module":       AppModuleUpdaterRule(out_dir=effective_out_dir, dry_run=dry_run),
    }

    if only:
        # Normalise: --only controllers,services
        requested = {o.strip().lower() for o in only}
        rules = [r for k, r in _all_rules.items() if k in requested]
        print(f"  Rules active: {[k for k in _all_rules if k in requested]}")
    else:
        rules = list(_all_rules.values())

    applier        = RuleApplier(rules)
    changes        = applier.apply_all(analysis, patterns)
    transformation = TransformationResult(changes=changes)
    print(f"  Transform : {len(changes)} changes proposed")

    # ── Risk assessment ────────────────────────────────────────────────────
    risk_by_change_id:   dict = {}
    reason_by_change_id: dict = {}

    for risk_rule in [
        ServiceRiskRule(),
        TemplateBindingRiskRule(),
        WatcherRiskRule(),
        DirectiveRiskRule(out_dir=effective_out_dir),
    ]:
        rb, rr = risk_rule.assess(analysis, patterns, transformation)
        risk_by_change_id.update(rb)
        reason_by_change_id.update(rr)

    changes = transformation.changes

    for change in changes:
        if change.id not in risk_by_change_id:
            risk_by_change_id[change.id]   = RiskLevel.SAFE
            reason_by_change_id[change.id] = "No specific risk pattern detected"

    risk = RiskResult(
        risk_by_change_id=risk_by_change_id,
        reason_by_change_id=reason_by_change_id,
    )

    # ── Risk summary — grouped by level, deduplicated ─────────────────────
    risk_groups: dict[str, list[str]] = {"MANUAL": [], "RISKY": [], "SAFE": []}
    seen_risk_names: set = set()
    for change in changes:
        level = risk_by_change_id.get(change.id, RiskLevel.SAFE)
        name  = _resolve_name(change, id_to_name, directive_id_to_name, analysis)
        if name == "unknown" or name in seen_risk_names:
            continue
        seen_risk_names.add(name)
        risk_groups[level.value.upper()].append(name)

    n_manual = len(risk_groups["MANUAL"])
    n_risky  = len(risk_groups["RISKY"])
    n_safe   = len(risk_groups["SAFE"])

    print(f"  Risk      : {n_safe} safe, {n_risky} risky, {n_manual} manual")
    if risk_groups["MANUAL"]:
        for name in risk_groups["MANUAL"]:
            reason = next(
                (reason_by_change_id[c.id] for c in changes
                 if _resolve_name(c, id_to_name, directive_id_to_name, analysis) == name
                 and c.id in reason_by_change_id),
                ""
            )
            print(f"    ⚠ MANUAL  {name} — {reason[:80]}")
    if risk_groups["RISKY"]:
        for name in risk_groups["RISKY"]:
            reason = next(
                (reason_by_change_id[c.id] for c in changes
                 if _resolve_name(c, id_to_name, directive_id_to_name, analysis) == name
                 and c.id in reason_by_change_id),
                ""
            )
            print(f"    ! RISKY   {name} — {reason[:80]}")

    # ── Validation (skip in dry-run / diff — files not written to real location) ──
    if dry_run or show_diff:
        tests_passed    = False
        snapshot_passed = False
        snapshot_failures = ["Skipped in dry-run / diff mode"]
    else:
        tests_passed, _ = TestRunner().run(str(repo_path))
        before_snapshot, after_snapshot = _find_snapshots(repo_path)
        snapshot_passed   = False
        snapshot_failures = []
        if before_snapshot.exists() and after_snapshot.exists():
            snapshot_passed, snapshot_failures = SnapshotComparator().compare(
                str(before_snapshot), str(after_snapshot)
            )
        else:
            missing = [str(p) for p in [before_snapshot, after_snapshot] if not p.exists()]
            snapshot_failures = [f"Snapshot file(s) missing: {', '.join(missing)}"]

    validation_summary = {
        "tests_passed":    tests_passed,
        "snapshot_passed": snapshot_passed,
        "tsc_passed":      None,
        "tsc_errors":      [],
        "failures": ([] if tests_passed else ["Tests failed"]) + snapshot_failures,
    }
    print(f"  Validate  : tests={tests_passed}, snapshot={snapshot_passed}")

    # ── Diff output ────────────────────────────────────────────────────────
    if show_diff and shadow_dir:
        real_out_dir = out_root / "angular-app"
        shadow_app   = shadow_dir / "angular-app"
        diffs = _collect_diffs(real_out_dir, shadow_app)

        if not diffs:
            print("\n  [DIFF] No changes — output is already up to date.")
        else:
            print(f"\n  [DIFF] {len(diffs)} file(s) would change:\n")
            for d in diffs:
                status = "NEW" if d["is_new"] else "MODIFIED"
                print(f"  [{status}] {d['file']}")
                print("  " + "-" * 60)
                # Print diff with indentation, limit to 80 lines
                diff_lines = d["diff"].splitlines()
                for line in diff_lines[:80]:
                    print("  " + line)
                if len(diff_lines) > 80:
                    print(f"  ... ({len(diff_lines) - 80} more lines)")
                print()

        # Clean up shadow dir
        shutil.rmtree(shadow_dir, ignore_errors=True)

    # ── Build report collections ───────────────────────────────────────────
    risk_by_level   = {"SAFE": [], "RISKY": [], "MANUAL": []}
    generated_files = []
    auto_modernized = []
    manual_required = []
    seen_names_per_level = {"SAFE": set(), "RISKY": set(), "MANUAL": set()}

    for change in changes:
        reason = getattr(change, "reason", "") or ""
        level  = risk_by_change_id.get(change.id, RiskLevel.SAFE)
        key    = level.value.upper()

        fname = _extract_generated_file(reason)
        if fname and fname not in generated_files:
            generated_files.append(fname)

        name = _resolve_name(change, id_to_name, directive_id_to_name, analysis)

        is_synthetic = (
            name == "unknown"
            or name.endswith("_html")
            or name == "routing_module"
        )
        if is_synthetic:
            continue

        if name not in seen_names_per_level[key]:
            seen_names_per_level[key].add(name)
            risk_by_level[key].append(name)

        if level == RiskLevel.MANUAL:
            if name not in manual_required:
                manual_required.append(name)
        else:
            if name not in auto_modernized:
                auto_modernized.append(name)

    transformation = TransformationResult(changes=changes)

    try:
        json_report = JSONReporter().render(analysis, patterns, transformation, risk, validation_summary)
        report_dict = json.loads(json_report)
    except Exception:
        report_dict = {}

    md_report = MarkdownReporter().render(analysis, patterns, transformation, risk, validation_summary)

    report_dict["risk"] = {"by_level": risk_by_level}
    report_dict["transformation"] = {
        "generated_files": generated_files,
        "auto_modernized": auto_modernized,
        "manual_required": manual_required,
    }
    if dry_run:
        report_dict["dry_run"] = True
    if "changes" not in report_dict:
        report_dict["changes"] = []

    # In dry-run / diff mode still write the report (read-only metadata)
    report_path = repo_path / ".evua_report.json"
    md_path     = repo_path / ".evua_report.md"

    report_json = json.dumps(report_dict, indent=2, ensure_ascii=False)
    report_path.write_text(report_json, encoding="utf-8", errors="replace")
    md_path.write_text(md_report, encoding="utf-8", errors="replace")

    print(f"  Reports   : {report_path}")

    # ── Clean summary box ──────────────────────────────────────────────────
    n_components = len([c for c in changes if "component" in (getattr(c, "reason", "") or "").lower() and "written" in (getattr(c, "reason", "") or "").lower()])
    n_services   = len([c for c in changes if "injectable" in (getattr(c, "reason", "") or "").lower()])
    n_pipes      = len([c for c in changes if "pipe" in (getattr(c, "after_id", "") or "").lower()])
    n_gen        = len(generated_files)

    print(f"\n  {'─'*56}")
    print(f"  {'EVUA Migration Summary':^56}")
    print(f"  {'─'*56}")
    print(f"  {'Project':<20} {repo_path.name}")
    print(f"  {'Files scanned':<20} {len(files)} ({n_js} JS)")
    print(f"  {'Classes found':<20} {n_classes}")
    print(f"  {'Routes migrated':<20} {n_routes}")
    print(f"  {'Changes proposed':<20} {len(changes)}")
    print(f"  {'Generated files':<20} {n_gen}")
    print(f"  {'Risk: safe/risky/manual':<20} {n_safe}/{n_risky}/{n_manual}")
    if n_manual > 0:
        print(f"  {'Needs manual review':<20} {', '.join(risk_groups['MANUAL'])}")
    print(f"  {'─'*56}")
    print(f"  Next steps:")
    print(f"    cd out/angular-app && npm install && ng serve")
    print(f"  {'─'*56}\n")

    # ── AI-assist post-processing ──────────────────────────────────────────
    if not dry_run and not show_diff:
        client = AIClient()
        ai_app_dir = real_out_dir / "src" / "app"
        stage = AIAssistStage(app_dir=ai_app_dir, analysis=analysis, client=client)
        stage.run()
    elif dry_run or show_diff:
        pass  # AI-assist not run in preview modes

    # ── TypeScript compilation validation ──────────────────────────────────
    if not dry_run and not show_diff and not skip_tsc:
        tsc_project_root = real_out_dir  # scaffold root = out/.tmp/angular-app
        print(f"\n  [tsc] Validating TypeScript compilation...")
        tsc_result = TscValidator(tsc_project_root).run()
        validation_summary["tsc_passed"] = tsc_result.passed
        validation_summary["tsc_errors"] = [e.to_dict() for e in tsc_result.errors[:50]]
        validation_summary["tsc_summary"] = tsc_result.error_summary
        validation_summary["tsc_found"]  = tsc_result.tsc_found
        if not tsc_result.passed and tsc_result.error_count > 0:
            validation_summary["failures"].append(
                f"TypeScript: {tsc_result.error_count} error(s)"
            )
        report_dict["validation"] = validation_summary
        report_dict["tsc_validation"] = tsc_result.to_dict()
        report_json = json.dumps(report_dict, indent=2, ensure_ascii=False)
        report_path.write_text(report_json, encoding="utf-8", errors="replace")
        _rewrite_md_report(repo_path, analysis, patterns, transformation, risk,
                           validation_summary, tsc_result)
        if tsc_result.passed:
            print(f"  Validate  : tsc ✓  (0 errors)")
        elif not tsc_result.tsc_found:
            print(f"  Validate  : tsc ✗  (tsc not found — install Node.js + TypeScript)")
        else:
            print(f"  Validate  : tsc ✗  ({tsc_result.error_count} errors)")
            for e in tsc_result.errors[:5]:
                fname = Path(e.file).name if hasattr(e, 'file') else '?'
                line  = getattr(e, 'line', '?')
                msg   = getattr(e, 'message', str(e))[:80]
                print(f"    {fname}:{line}  {msg}")
    elif skip_tsc:
        print("  [tsc] Skipped (--skip-tsc)")

    return True


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="EVUA — AngularJS → Angular migration engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py src/my-app               # full migration
  python cli.py src/my-app --dry-run     # preview — no files written
  python cli.py src/my-app --diff        # show unified diffs
  python cli.py src/my-app --only controllers,services
  python cli.py src/my-app --batch       # CI/harness mode (always exit 0)
  python cli.py src/my-app --skip-tsc    # skip TypeScript compilation check
  python cli.py src/my-app --ai-assist   # AI-complete stubs (needs GEMINI_API_KEY)
""",
    )
    parser.add_argument("repo",    nargs="?", help="Path to AngularJS repo")
    parser.add_argument("--batch", action="store_true",
                        help="Batch mode — always exit 0 (for harness)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Analyse and plan migration but write nothing")
    parser.add_argument("--diff",  action="store_true",
                        help="Show unified diffs of what would change")
    parser.add_argument("--only",  type=str, default=None,
                        help="Comma-separated subset of rules: controllers,services,http,watch")
    parser.add_argument(
                        "--ai-assist", action="store_true",
                        help="Enable AI completion of generated Angular stubs")
    parser.add_argument(
                        "--skip-tsc", action="store_true",
                        help="Skip TypeScript compilation check (faster runs, CI mode)")
    args = parser.parse_args()

    if not args.repo:
        parser.print_help()
        sys.exit(1)

    only_list = [s.strip() for s in args.only.split(",")] if args.only else None

    def _run(out_root):
        return run_pipeline(
            repo_path=args.repo,
            out_root=out_root,
            dry_run=args.dry_run,
            show_diff=args.diff,
            only=only_list,
            batch=args.batch,
            ai_assist=args.ai_assist,
            skip_tsc=args.skip_tsc,
        )

    runner = PipelineRunner(_run)
    ok = runner.run()

    if args.batch:
        sys.exit(0)
    else:
        sys.exit(0 if ok else 1)