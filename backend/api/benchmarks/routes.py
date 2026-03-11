import sys
import json
import asyncio
import tempfile
import shutil
import difflib
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends
from api.auth.utils import get_current_user
from api.auth.models import UserOut
from api.sessions import store as session_store

router = APIRouter(prefix="/benchmarks", tags=["benchmarks"])

# Resolve the benchmarks directory relative to this project
_ENGINE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "engine"
_BENCHMARKS_DIR = _ENGINE_DIR / "benchmarks" / "angularjs"


def _get_benchmark_list() -> list[dict]:
    """Scan the benchmarks directory and return metadata for each."""
    benchmarks = []
    if not _BENCHMARKS_DIR.exists():
        return benchmarks

    for d in sorted(_BENCHMARKS_DIR.iterdir()):
        if not d.is_dir():
            continue
        readme = d / "README.md"
        description = ""
        if readme.exists():
            lines = readme.read_text(encoding="utf-8", errors="replace").strip().splitlines()
            # Use first non-heading line as description, or first line
            for line in lines:
                stripped = line.strip().lstrip("#").strip()
                if stripped:
                    description = stripped
                    break

        # Count source files
        repo_dir = d / "repo" / "src" if (d / "repo" / "src").exists() else d / "repo"
        file_count = 0
        if repo_dir.exists():
            file_count = sum(1 for f in repo_dir.rglob("*") if f.is_file())

        benchmarks.append({
            "id": d.name,
            "name": d.name.replace("-", " ").replace("_", " ").title(),
            "description": description,
            "path": str(d),
            "file_count": file_count,
        })
    return benchmarks


@router.get("")
async def list_benchmarks(current_user: UserOut = Depends(get_current_user)):
    return _get_benchmark_list()


def _unified_diff(before_text: str, after_text: str, filename: str) -> str:
    before_lines = before_text.splitlines(keepends=True)
    after_lines = after_text.splitlines(keepends=True)
    diff = difflib.unified_diff(
        before_lines, after_lines,
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
        lineterm="",
    )
    return "".join(diff)


def _collect_diffs_with_content(out_dir: Path, shadow_dir: Path) -> list[dict]:
    """Collect diffs with full before/after content for storage."""
    diffs = []
    for shadow_file in sorted(shadow_dir.rglob("*")):
        if not shadow_file.is_file():
            continue
        rel = shadow_file.relative_to(shadow_dir)
        real_file = out_dir / rel

        after_text = shadow_file.read_text(encoding="utf-8", errors="replace")
        before_text = real_file.read_text(encoding="utf-8", errors="replace") if real_file.exists() else ""

        if before_text == after_text:
            continue

        diff = _unified_diff(before_text, after_text, str(rel))
        diffs.append({
            "file": str(rel),
            "diff": diff,
            "is_new": not real_file.exists(),
            "before_content": before_text,
            "after_content": after_text,
        })
    return diffs


def _run_migration_sync(repo_path: str, out_root: str) -> dict:
    """
    Run the migration pipeline synchronously and return diffs + report.
    This is called in a thread pool to avoid blocking the event loop.
    """
    # Add engine directory to path so imports work
    engine_dir = str(_ENGINE_DIR)
    if engine_dir not in sys.path:
        sys.path.insert(0, engine_dir)

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
    from pipeline.transformation.applier import RuleApplier
    from pipeline.transformation.result import TransformationResult
    from pipeline.risk.rules.angularjs.watcher_risk import WatcherRiskRule
    from pipeline.risk.rules.angularjs.template_binding_risk import TemplateBindingRiskRule
    from pipeline.risk.rules.angularjs.directive_risk import DirectiveRiskRule
    from pipeline.risk.rules.service_risk import ServiceRiskRule
    from pipeline.risk.result import RiskResult
    from pipeline.risk.levels import RiskLevel
    from pipeline.reporting.reporters.json_reporter import JSONReporter

    repo = Path(repo_path).resolve()
    out = Path(out_root).resolve()
    real_out_dir = out / "angular-app"

    shadow_dir = Path(tempfile.mkdtemp(prefix="evua_shadow_"))
    effective_out_dir = shadow_dir / "angular-app"

    timeline_events = []

    def log_event(stage, message, detail=None, level="info"):
        timeline_events.append({
            "stage": stage,
            "message": message,
            "detail": detail,
            "level": level,
        })

    try:
        # Ingestion
        scanner = FileScanner()
        files = scanner.scan(str(repo))
        classifier = FileClassifier()
        files_by_type = {
            FileType.JS: [p for p in files if classifier.classify(p) == FileType.JS],
            FileType.HTML: [p for p in files if classifier.classify(p) == FileType.HTML],
            FileType.PY: [p for p in files if classifier.classify(p) == FileType.PY],
            FileType.JAVA: [p for p in files if classifier.classify(p) == FileType.JAVA],
        }
        n_js = len(files_by_type[FileType.JS])
        log_event("ingestion", f"Scanned {len(files)} files ({n_js} JavaScript)", {"total": len(files), "js": n_js})

        # Analysis
        dispatcher = AnalyzerDispatcher()
        analysis: AnalysisResult = dispatcher.dispatch(files_by_type)
        n_classes = sum(len(m.classes) for m in analysis.modules)
        n_http = len(analysis.http_calls)
        n_directives = len(getattr(analysis, "directives", []) or [])
        n_routes = len(getattr(analysis, "routes", []) or [])
        log_event("analysis", f"Found {n_classes} classes, {n_http} HTTP calls, {n_directives} directives, {n_routes} routes", {
            "classes": n_classes, "http_calls": n_http, "directives": n_directives, "routes": n_routes
        })

        # Pattern detection
        roles = {}
        confidence = {}
        for detector in [ControllerDetector(), HttpDetector(), SimpleWatchDetector(), ServiceDetector(), DirectiveDetector()]:
            r, c = detector.detect(analysis)
            for k, v in r.items():
                roles.setdefault(k, []).extend(v)
            confidence.update(c)
        patterns = PatternResult(roles_by_node=roles, confidence_by_node=confidence)
        log_event("patterns", f"Detected {len(roles)} pattern nodes")

        # Transformation
        rules = [
            RouteMigratorRule(out_dir=effective_out_dir, dry_run=False),
            ControllerToComponentRule(out_dir=effective_out_dir, dry_run=False),
            ServiceToInjectableRule(out_dir=effective_out_dir, dry_run=False),
            HttpToHttpClientRule(out_dir=effective_out_dir, dry_run=False),
            SimpleWatchToRxjsRule(out_dir=effective_out_dir, dry_run=False),
        ]
        applier = RuleApplier(rules)
        changes = applier.apply_all(analysis, patterns)
        transformation = TransformationResult(changes=changes)
        log_event("transformation", f"Applied {len(changes)} transformations", {"change_count": len(changes)})

        # Risk assessment
        risk_by_change_id = {}
        reason_by_change_id = {}
        for risk_rule in [ServiceRiskRule(), TemplateBindingRiskRule(), WatcherRiskRule(), DirectiveRiskRule(out_dir=effective_out_dir)]:
            rb, rr = risk_rule.assess(analysis, patterns, transformation)
            risk_by_change_id.update(rb)
            reason_by_change_id.update(rr)

        for change in changes:
            if change.id not in risk_by_change_id:
                risk_by_change_id[change.id] = RiskLevel.SAFE
                reason_by_change_id[change.id] = "No specific risk pattern detected"

        risk = RiskResult(risk_by_change_id=risk_by_change_id, reason_by_change_id=reason_by_change_id)

        safe_count = sum(1 for v in risk_by_change_id.values() if v == RiskLevel.SAFE)
        risky_count = sum(1 for v in risk_by_change_id.values() if v == RiskLevel.RISKY)
        manual_count = sum(1 for v in risk_by_change_id.values() if v == RiskLevel.MANUAL)
        risk_summary = {"SAFE": safe_count, "RISKY": risky_count, "MANUAL": manual_count}
        log_event("risk", f"Risk assessment: {safe_count} safe, {risky_count} risky, {manual_count} manual", risk_summary)

        # Collect diffs
        diffs = _collect_diffs_with_content(real_out_dir, effective_out_dir)
        log_event("reporting", f"Generated diffs for {len(diffs)} files", {"file_count": len(diffs)})

        # Try to get report
        report_dict = {}
        try:
            json_report = JSONReporter().render(analysis, patterns, transformation, risk, {})
            report_dict = json.loads(json_report)
        except Exception:
            pass

        # Attach risk info to diffs by matching file paths to changes
        # Build a map of generated file -> (risk_level, reason)
        file_risk_map = {}
        import re
        for change in changes:
            reason = getattr(change, "reason", "") or ""
            for marker in ("written to ", "migrated into "):
                if marker in reason:
                    raw = reason.split(marker, 1)[-1].strip()
                    raw = re.sub(r'\s*\(.*\)\s*$', '', raw).strip()
                    fname = Path(raw).name
                    level = risk_by_change_id.get(change.id, RiskLevel.SAFE)
                    file_risk_map[fname] = (level.value.upper(), reason_by_change_id.get(change.id, ""))
                    break

        for d in diffs:
            fname = Path(d["file"]).name
            if fname in file_risk_map:
                d["risk_level"] = file_risk_map[fname][0]
                d["reason"] = file_risk_map[fname][1]
            else:
                d["risk_level"] = "SAFE"
                d["reason"] = ""

        return {
            "diffs": diffs,
            "timeline_events": timeline_events,
            "risk_summary": risk_summary,
            "report": report_dict,
        }

    finally:
        shutil.rmtree(shadow_dir, ignore_errors=True)


@router.post("/{benchmark_id}/migrate")
async def run_migration(
    benchmark_id: str,
    current_user: UserOut = Depends(get_current_user),
):
    # Find the benchmark
    benchmarks = _get_benchmark_list()
    benchmark = next((b for b in benchmarks if b["id"] == benchmark_id), None)
    if not benchmark:
        raise HTTPException(status_code=404, detail="Benchmark not found")

    bench_path = Path(benchmark["path"])
    repo_path = bench_path / "repo"
    if not repo_path.exists():
        repo_path = bench_path  # fallback if no repo/ subdirectory

    # Create session
    session_id = await session_store.create_session(
        user_id=current_user.id,
        benchmark_id=benchmark_id,
        benchmark_name=benchmark["name"],
    )

    await session_store.add_timeline_event(
        session_id, "ingestion", f"Starting migration of {benchmark['name']}"
    )

    try:
        # Run the pipeline in a thread to avoid blocking
        out_root = Path("out").resolve()
        result = await asyncio.get_event_loop().run_in_executor(
            None, _run_migration_sync, str(repo_path), str(out_root)
        )

        # Store timeline events
        for evt in result["timeline_events"]:
            await session_store.add_timeline_event(
                session_id, evt["stage"], evt["message"], evt.get("detail"), evt.get("level", "info")
            )

        # Store file diffs
        await session_store.store_file_diffs(session_id, result["diffs"])

        # Update session status
        await session_store.update_session_status(
            session_id,
            "completed" if result["diffs"] else "completed",
            file_count=len(result["diffs"]),
            risk_summary=result["risk_summary"],
        )

        await session_store.add_timeline_event(
            session_id, "reporting", "Migration pipeline completed successfully"
        )

        return {"session_id": session_id, "file_count": len(result["diffs"])}

    except Exception as e:
        await session_store.update_session_status(session_id, "failed")
        await session_store.add_timeline_event(
            session_id, "reporting", f"Migration failed: {str(e)}", level="error"
        )
        raise HTTPException(status_code=500, detail=f"Migration failed: {str(e)}")
