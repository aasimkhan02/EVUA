import sys
from pathlib import Path
import argparse

from pipeline.ingestion.scanner import FileScanner
from pipeline.ingestion.classifier import FileClassifier, FileType
from pipeline.analysis.dispatcher import AnalyzerDispatcher
from pipeline.analysis.result import AnalysisResult

from pipeline.patterns.detectors.angularjs.controller_detector import ControllerDetector
from pipeline.patterns.detectors.angularjs.http_detector import HttpDetector
from pipeline.patterns.detectors.angularjs.simple_watch_detector import SimpleWatchDetector
from pipeline.patterns.detectors.angularjs.service_detector import ServiceDetector
from pipeline.patterns.result import PatternResult

from pipeline.transformation.rules.angularjs.controller_to_component import ControllerToComponentRule
from pipeline.transformation.rules.angularjs.http_to_httpclient import HttpToHttpClientRule
from pipeline.transformation.rules.angularjs.simple_watch_to_rxjs import SimpleWatchToRxjsRule
from pipeline.transformation.rules.angularjs.service_to_injectable import ServiceToInjectableRule
from pipeline.transformation.applier import RuleApplier
from pipeline.transformation.result import TransformationResult

from pipeline.risk.rules.angularjs.watcher_risk import WatcherRiskRule
from pipeline.risk.rules.angularjs.template_binding_risk import TemplateBindingRiskRule
from pipeline.risk.rules.service_risk import ServiceRiskRule
from pipeline.risk.result import RiskResult
from pipeline.risk.levels import RiskLevel

from pipeline.reporting.reporters.json_reporter import JSONReporter
from pipeline.reporting.reporters.markdown_reporter import MarkdownReporter

from pipeline.validation.runners.tests import TestRunner
from pipeline.validation.comparators.snapshot import SnapshotComparator

from orchestration.pipeline_runner import PipelineRunner


def run_pipeline(repo_path: str) -> bool:
    repo_path = Path(repo_path).resolve()
    print(f"\nRunning migration pipeline on: {repo_path}")

    # ── 1. Ingestion ───────────────────────────────────────────────────────
    scanner = FileScanner()
    files = scanner.scan(str(repo_path))

    classifier = FileClassifier()
    files_by_type = {
        FileType.JS:   [p for p in files if classifier.classify(p) == FileType.JS],
        FileType.HTML: [p for p in files if classifier.classify(p) == FileType.HTML],
        FileType.PY:   [p for p in files if classifier.classify(p) == FileType.PY],
        FileType.JAVA: [p for p in files if classifier.classify(p) == FileType.JAVA],
    }
    print(f"  Ingestion : {len(files)} files  ({len(files_by_type[FileType.JS])} JS)")

    # ── 2. Analysis ────────────────────────────────────────────────────────
    dispatcher = AnalyzerDispatcher()
    analysis: AnalysisResult = dispatcher.dispatch(files_by_type)
    print(f"  Analysis  : {sum(len(m.classes) for m in analysis.modules)} classes, "
          f"{len(analysis.http_calls)} http calls")

    # ── 3. Patterns ────────────────────────────────────────────────────────
    roles: dict = {}
    confidence: dict = {}

    for detector in [
        ControllerDetector(),
        HttpDetector(),
        SimpleWatchDetector(),
        ServiceDetector(),
    ]:
        r, c = detector.detect(analysis)
        for k, v in r.items():
            roles.setdefault(k, []).extend(v)
        confidence.update(c)

    patterns = PatternResult(roles_by_node=roles, confidence_by_node=confidence)
    print(f"  Patterns  : {len(roles)} nodes matched")

    # ── 4. Transformation ──────────────────────────────────────────────────
    rules = [
        ControllerToComponentRule(),
        ServiceToInjectableRule(),
        HttpToHttpClientRule(),
        SimpleWatchToRxjsRule(),
    ]
    applier = RuleApplier(rules)
    changes = applier.apply_all(analysis, patterns)
    transformation = TransformationResult(changes=changes)
    print(f"  Transform : {len(changes)} changes proposed")

    # ── 5. Risk (all three rules) ──────────────────────────────────────────
    risk_by_change_id: dict = {}
    reason_by_change_id: dict = {}

    for risk_rule in [ServiceRiskRule(), TemplateBindingRiskRule(), WatcherRiskRule()]:
        rb, rr = risk_rule.assess(analysis, patterns, transformation)
        # Later rules override earlier ones for the same change (intentional priority)
        risk_by_change_id.update(rb)
        reason_by_change_id.update(rr)

    # Ensure every change has a risk level (default SAFE)
    for change in changes:
        if change.id not in risk_by_change_id:
            risk_by_change_id[change.id]   = RiskLevel.SAFE
            reason_by_change_id[change.id] = "No specific risk pattern detected"

    risk = RiskResult(
        risk_by_change_id=risk_by_change_id,
        reason_by_change_id=reason_by_change_id,
    )

    print("  Risk:")
    for change in changes:
        level  = risk_by_change_id.get(change.id, RiskLevel.SAFE)
        reason = reason_by_change_id.get(change.id, "")
        print(f"    - {change.before_id[:12]}... → {level}  ({reason[:60]})")

    # ── 6. Validation ──────────────────────────────────────────────────────
    tests_passed, _ = TestRunner().run(str(repo_path))

    before_snapshot = repo_path / "snapshots" / "before.json"
    after_snapshot  = repo_path / "snapshots" / "after.json"
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
        "failures": ([] if tests_passed else ["Tests failed"]) + snapshot_failures,
    }
    print(f"  Validate  : tests={tests_passed}, snapshot={snapshot_passed}")

    # ── 7. Reporting ───────────────────────────────────────────────────────
    # Build a JSON-serialisable risk summary used by the evaluation harness
    risk_by_level: dict = {"SAFE": [], "RISKY": [], "MANUAL": []}
    for change in changes:
        level = risk_by_change_id.get(change.id, RiskLevel.SAFE)
        key   = level.value.upper()               # "safe" → "SAFE"
        risk_by_level.get(key, risk_by_level["SAFE"]).append(change.before_id)

    generated_files = []
    auto_modernized = []
    manual_required = []
    for change in changes:
        level = risk_by_change_id.get(change.id, RiskLevel.SAFE)
        if level == RiskLevel.MANUAL:
            manual_required.append(change.before_id)
        else:
            auto_modernized.append(change.before_id)
        # Extract file path from reason string
        if "written to " in change.reason:
            generated_files.append(change.reason.split("written to ")[-1].strip())

    # Full JSON report (harness-parseable)
    json_report  = JSONReporter().render(analysis, patterns, transformation, risk, validation_summary)
    md_report    = MarkdownReporter().render(analysis, patterns, transformation, risk, validation_summary)

    # Augment the JSON with harness-friendly top-level keys
    import json
    report_dict = json.loads(json_report)
    report_dict["risk"]            = {"by_level": risk_by_level}
    report_dict["transformation"]  = {
        "generated_files": generated_files,
        "auto_modernized": auto_modernized,
        "manual_required": manual_required,
    }

    report_path = repo_path / ".evua_report.json"
    md_path     = repo_path / ".evua_report.md"
    report_path.write_text(json.dumps(report_dict, indent=2), encoding="utf-8")
    md_path.write_text(md_report, encoding="utf-8")

    print(f"\n  Reports   : {report_path}")
    print(  "  Pipeline run complete.\n")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", nargs="?", help="Path to AngularJS repo")
    parser.add_argument("--batch", action="store_true",
                        help="Batch mode — always exit 0 so harness continues")
    args = parser.parse_args()

    if args.batch:
        run_pipeline(args.repo)
        sys.exit(0)

    if not args.repo:
        print("Usage: python cli.py <path-to-repo>")
        sys.exit(1)

    runner = PipelineRunner(lambda: run_pipeline(args.repo))
    ok = runner.run()
    sys.exit(0 if ok else 1)