import sys
from pathlib import Path
import argparse

from pipeline.ingestion.scanner import FileScanner
from pipeline.ingestion.classifier import FileClassifier, FileType
from pipeline.analysis.dispatcher import AnalyzerDispatcher
from pipeline.analysis.builder import IRBuilder
from pipeline.analysis.result import AnalysisResult

from pipeline.patterns.detectors.angularjs.controller_detector import ControllerDetector
from pipeline.patterns.result import PatternResult

from pipeline.transformation.rules.angularjs.controller_to_component import ControllerToComponentRule
from pipeline.transformation.result import TransformationResult

from pipeline.risk.rules.angularjs.watcher_risk import WatcherRiskRule
from pipeline.risk.levels import RiskLevel

from pipeline.reporting.reporters.json_reporter import JSONReporter
from pipeline.reporting.reporters.markdown_reporter import MarkdownReporter

from pipeline.validation.runners.tests import TestRunner
from pipeline.validation.comparators.snapshot import SnapshotComparator

from orchestration.pipeline_runner import PipelineRunner


def run_pipeline(repo_path: str) -> bool:
    repo_path = Path(repo_path).resolve()
    print(f"▶ Running migration pipeline on: {repo_path}")

    # 1) Ingestion
    scanner = FileScanner()
    files = scanner.scan(str(repo_path))

    classifier = FileClassifier()
    files_by_type = {
        FileType.JS: [p for p in files if classifier.classify(p) == FileType.JS],
        FileType.HTML: [p for p in files if classifier.classify(p) == FileType.HTML],
        FileType.PY: [p for p in files if classifier.classify(p) == FileType.PY],
        FileType.JAVA: [p for p in files if classifier.classify(p) == FileType.JAVA],
    }

    print(f"  Found {len(files_by_type[FileType.JS])} JS files")

    # 2) Analysis (USE DISPATCHER, NOT JSAnalyzer DIRECTLY)
    dispatcher = AnalyzerDispatcher()
    analysis: AnalysisResult = dispatcher.dispatch(files_by_type)

    print(f"  Analysis: {sum(len(m.classes) for m in analysis.modules)} classes found")
    print(f"  Analysis: {len(analysis.http_calls)} http/q calls extracted")

    # 3) Patterns
    detector = ControllerDetector()
    roles, confidence = detector.detect(analysis)

    patterns = PatternResult(
        roles_by_node=roles,
        confidence_by_node=confidence
    )

    print(f"  Patterns: {len(roles)} controllers detected")

    # 4) Transformation
    rule = ControllerToComponentRule()
    changes = rule.apply(analysis, patterns)

    transformation = TransformationResult(changes=changes)

    print(f"  Transformation: {len(changes)} changes proposed")

    # 5) Risk
    risk_rule = WatcherRiskRule()
    risk_by_change, reason_by_change = risk_rule.assess(analysis, patterns, transformation)

    print("  Risk:")
    for change in changes:
        risk = risk_by_change.get(change.id, RiskLevel.SAFE)
        reason = reason_by_change.get(change.id, "")
        print(f"    - Change {change.before_id} → {risk} ({reason})")

    # 6) Validation (tests + snapshot)
    tests_passed, _ = TestRunner().run(str(repo_path))

    before_snapshot = repo_path / "snapshots" / "before.json"
    after_snapshot = repo_path / "snapshots" / "after.json"

    snapshot_passed = False
    snapshot_failures = []

    if before_snapshot.exists() and after_snapshot.exists():
        snapshot_passed, snapshot_failures = SnapshotComparator().compare(
            str(before_snapshot),
            str(after_snapshot),
        )
    else:
        missing = []
        if not before_snapshot.exists():
            missing.append(str(before_snapshot))
        if not after_snapshot.exists():
            missing.append(str(after_snapshot))
        snapshot_failures = [f"Snapshot file(s) missing: {', '.join(missing)}"]

    validation_summary = {
        "tests_passed": tests_passed,
        "snapshot_passed": snapshot_passed,
        "failures": ([] if tests_passed else ["Tests failed"]) + snapshot_failures,
    }

    print(f"  Validation: tests_passed={tests_passed}, snapshot_passed={snapshot_passed}")

    # 7) Reporting
    json_report = JSONReporter().render(
        analysis, patterns, transformation, (risk_by_change, reason_by_change), validation_summary
    )
    md_report = MarkdownReporter().render(
        analysis, patterns, transformation, (risk_by_change, reason_by_change), validation_summary
    )

    with open("report.json", "w", encoding="utf-8") as f:
        f.write(json_report)

    with open("report.md", "w", encoding="utf-8") as f:
        f.write(md_report)

    print("\n📄 Reports saved: report.json, report.md")
    print("\n✅ Pipeline run complete.")

    # 🔴 Critical: return validation result so rollback can happen
    return tests_passed and snapshot_passed


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", nargs="?", help="Path to repo")
    parser.add_argument("--batch", action="store_true", help="Batch mode for eval harness")
    args = parser.parse_args()

    if args.batch:
        ok = run_pipeline(args.repo)
        sys.exit(0 if ok else 1)

    if not args.repo:
        print("Usage: python cli.py <path-to-repo>")
        sys.exit(1)

    runner = PipelineRunner(lambda: run_pipeline(args.repo))
    ok = runner.run()

    if not ok:
        print("\n↩️ Changes rolled back due to validation failure.")
    else:
        print("\n🎉 Changes committed successfully.")
