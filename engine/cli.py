import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


from pathlib import Path
import argparse
import json
import traceback
import re

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


def _find_snapshots(repo_path: Path):
    # Also check parent/snapshots (bench/snapshots)
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


def _resolve_name(change, id_to_name: dict, analysis) -> str:
    name = id_to_name.get(change.before_id)
    if name:
        return name

    for call in getattr(analysis, "http_calls", []):
        if getattr(call, "id", None) == change.before_id:
            owner = getattr(call, "owner_controller", None)
            if owner:
                return owner

    return "unknown"   # prevent UUID leakage into reports


def _extract_file_from_reason(reason: str) -> str:
    """Extract file path from reason string using multiple patterns."""
    if not reason:
        return None
    
    # Pattern 1: "Written: path/to/file"
    if "Written:" in reason:
        parts = reason.split("Written:", 1)
        if len(parts) > 1:
            return parts[1].strip()
    
    # Pattern 2: "Migrating: ... -> path/to/file"
    if "Migrating:" in reason:
        # Look for arrow or "to" followed by path
        parts = reason.split("Migrating:", 1)[1]
        # Try to find path after "->" or "to"
        if "->" in parts:
            path_part = parts.split("->", 1)[1].strip()
            return path_part
        elif " to " in parts:
            path_part = parts.split(" to ", 1)[1].strip()
            return path_part
    
    # Pattern 3: Look for .ts or .html file paths
    match = re.search(r'[\w\\/]+\.(ts|html|js|service\.ts|component\.ts)', reason)
    if match:
        return match.group(0)
    
    return None


def run_pipeline(repo_path: str) -> bool:
    repo_path = Path(repo_path).resolve()
    print(f"\n{'='*60}")
    print(f"Running migration pipeline on: {repo_path}")
    print(f"{'='*60}")

    # DEBUG: Check if running in batch mode
    import sys
    is_batch = '--batch' in sys.argv
    print(f" DEBUG - Batch mode: {is_batch}")

    scanner    = FileScanner()
    files      = scanner.scan(str(repo_path))
    classifier = FileClassifier()

    files_by_type = {
        FileType.JS:   [p for p in files if classifier.classify(p) == FileType.JS],
        FileType.HTML: [p for p in files if classifier.classify(p) == FileType.HTML],
        FileType.PY:   [p for p in files if classifier.classify(p) == FileType.PY],
        FileType.JAVA: [p for p in files if classifier.classify(p) == FileType.JAVA],
    }
    print(f"  Ingestion : {len(files)} files  ({len(files_by_type[FileType.JS])} JS)")

    dispatcher = AnalyzerDispatcher()
    analysis: AnalysisResult = dispatcher.dispatch(files_by_type)
    print(f"  Analysis  : {sum(len(m.classes) for m in analysis.modules)} classes, "
          f"{len(analysis.http_calls)} http calls")

    id_to_name = _build_id_to_name(analysis)

    roles:      dict = {}
    confidence: dict = {}

    for detector in [ControllerDetector(), HttpDetector(), SimpleWatchDetector(), ServiceDetector()]:
        r, c = detector.detect(analysis)
        for k, v in r.items():
            roles.setdefault(k, []).extend(v)
        confidence.update(c)

    patterns = PatternResult(roles_by_node=roles, confidence_by_node=confidence)
    print(f"  Patterns  : {len(roles)} nodes matched")

    rules = [
        ControllerToComponentRule(),
        ServiceToInjectableRule(),
        HttpToHttpClientRule(),
        SimpleWatchToRxjsRule(),
    ]
    applier        = RuleApplier(rules)
    changes        = applier.apply_all(analysis, patterns)
    transformation = TransformationResult(changes=changes)
    print(f"  Transform : {len(changes)} changes proposed")
    
    # DEBUG: Check changes after transformation
    print(f" DEBUG - changes object type: {type(changes)}")
    print(f" DEBUG - changes length: {len(changes)}")
    if changes:
        print(f" DEBUG - First change type: {type(changes[0])}")
        print(f" DEBUG - First change dir: {dir(changes[0])[:10]}")
        try:
            print(f" DEBUG - First change __dict__: {changes[0].__dict__}")
        except:
            print(f" DEBUG - First change (str): {str(changes[0])}")
    else:
        print(f" DEBUG - WARNING: No changes generated!")

    risk_by_change_id:   dict = {}
    reason_by_change_id: dict = {}

    for risk_rule in [ServiceRiskRule(), TemplateBindingRiskRule(), WatcherRiskRule()]:
        rb, rr = risk_rule.assess(analysis, patterns, transformation)
        risk_by_change_id.update(rb)
        reason_by_change_id.update(rr)

    for change in changes:
        if change.id not in risk_by_change_id:
            risk_by_change_id[change.id]   = RiskLevel.SAFE
            reason_by_change_id[change.id] = "No specific risk pattern detected"

    risk = RiskResult(
        risk_by_change_id=risk_by_change_id,
        reason_by_change_id=reason_by_change_id,
    )

    print("  Risk:")
    seen_ids = set()
    for change in changes:
        if change.id in seen_ids:
            continue
        seen_ids.add(change.id)
        level  = risk_by_change_id.get(change.id, RiskLevel.SAFE)
        reason = reason_by_change_id.get(change.id, "")
        name   = _resolve_name(change, id_to_name, analysis)
        print(f"    - {name:30s} => {level}  ({reason[:60]})")

    tests_passed, _ = TestRunner().run(str(repo_path))
    before_snapshot, after_snapshot = _find_snapshots(repo_path)
    snapshot_passed = False
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

    risk_by_level = {"SAFE": [], "RISKY": [], "MANUAL": []}
    generated_files = []
    auto_modernized = []
    manual_required = []

    seen_names_global = set()
    seen_names_per_level = {"SAFE": set(), "RISKY": set(), "MANUAL": set()}

    for change in changes:
        level = risk_by_change_id.get(change.id, RiskLevel.SAFE)
        key   = level.value.upper()
        name  = _resolve_name(change, id_to_name, analysis)

        if name == "unknown":
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

        # Extract file paths from reason
        reason = getattr(change, "reason", "") or ""
        file_path = _extract_file_from_reason(reason)
        if file_path:
            # Normalize path to relative path from project root
            if "out/angular-app" in file_path:
                file_path = file_path.split("out/angular-app/", 1)[-1]
            if file_path not in generated_files:
                generated_files.append(file_path)
                print(f" DEBUG - Captured generated file: {file_path} from reason: {reason[:50]}...")

    # DEBUG: Show what we're about to report
    print(f"\n DEBUG - Before JSON report generation:")
    print(f"  changes count: {len(changes)}")
    print(f"  risk_by_level: {risk_by_level}")
    print(f"  auto_modernized: {auto_modernized}")
    print(f"  manual_required: {manual_required}")
    print(f"  generated_files: {generated_files}")

    transformation = TransformationResult(changes=changes)

    # DEBUG: Check JSONReporter
    print(f" DEBUG - Generating JSON report...")
    try:
        json_report = JSONReporter().render(analysis, patterns, transformation, risk, validation_summary)
        print(f" DEBUG - JSON report length: {len(json_report)}")
        print(f" DEBUG - JSON report preview (first 300 chars):")
        print(json_report[:300])
    except Exception as e:
        print(f" DEBUG - Error generating JSON report: {e}")
        traceback.print_exc()
        json_report = "{}"

    md_report   = MarkdownReporter().render(analysis, patterns, transformation, risk, validation_summary)

    # DEBUG: Parse the JSON report and check its structure
    print(f" DEBUG - Parsing JSON report...")
    try:
        report_dict = json.loads(json_report)
        print(f" DEBUG - report_dict keys: {list(report_dict.keys())}")
        print(f" DEBUG - report_dict['changes'] type: {type(report_dict.get('changes'))}")
        print(f" DEBUG - report_dict['changes'] length: {len(report_dict.get('changes', []))}")
        
        if report_dict.get('changes'):
            print(f" DEBUG - First change in report_dict: {report_dict['changes'][0]}")
        else:
            print(f" DEBUG - WARNING: report_dict['changes'] is empty!")
            
            # Check if changes were lost in JSON serialization
            if changes:
                print(f" DEBUG - BUT we have {len(changes)} changes in memory!")
                print(f" DEBUG - Attempting to manually reconstruct changes...")
                
                # Try to manually create a changes list
                manual_changes = []
                for c in changes:
                    try:
                        manual_changes.append({
                            "before_id": getattr(c, "before_id", "unknown"),
                            "after_id": getattr(c, "after_id", "unknown"),
                            "reason": getattr(c, "reason", ""),
                            "id": getattr(c, "id", "unknown"),
                        })
                    except:
                        pass
                
                print(f" DEBUG - Manual changes reconstruction: {manual_changes}")
    except Exception as e:
        print(f" DEBUG - Error parsing JSON report: {e}")
        traceback.print_exc()
        report_dict = {}

    # Add the risk and transformation data
    report_dict["risk"] = {"by_level": risk_by_level}
    report_dict["transformation"] = {
        "generated_files": generated_files,
        "auto_modernized": auto_modernized,
        "manual_required": manual_required,
    }

    # Ensure changes exists even if empty
    if "changes" not in report_dict:
        print(f" DEBUG - Adding missing 'changes' key to report_dict")
        report_dict["changes"] = []

    report_path = repo_path / ".evua_report.json"
    md_path     = repo_path / ".evua_report.md"
    
    # DEBUG: Write report and verify
    print(f" DEBUG - Writing report to: {report_path}")
    try:
        report_json = json.dumps(report_dict, indent=2, ensure_ascii=False)
        report_path.write_text(report_json, encoding="utf-8", errors="replace")
        md_path.write_text(md_report, encoding="utf-8", errors="replace")
        
        # Verify the written file
        if report_path.exists():
            file_size = report_path.stat().st_size
            print(f" DEBUG - Report written successfully. Size: {file_size} bytes")
            
            # Read it back to verify
            written_content = report_path.read_text(encoding="utf-8")
            written_dict = json.loads(written_content)
            print(f" DEBUG - Written report changes count: {len(written_dict.get('changes', []))}")
            print(f" DEBUG - Written report generated_files: {written_dict.get('transformation', {}).get('generated_files', [])}")
        else:
            print(f" DEBUG - Report file was not created!")
    except Exception as e:
        print(f" DEBUG - Error writing report: {e}")
        traceback.print_exc()

    print(f"\n  Reports   : {report_path}")
    print(f"  Pipeline run complete.\n")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", nargs="?", help="Path to AngularJS repo")
    parser.add_argument("--batch", action="store_true",
                        help="Batch mode -- always exit 0 so harness continues")
    args = parser.parse_args()

    if not args.repo:
        print("Usage: python cli.py <path-to-repo>")
        sys.exit(1)

    print(f" DEBUG - Command line args: {sys.argv}")
    print(f" DEBUG - Batch mode: {args.batch}")

    # Always use PipelineRunner for consistency
    runner = PipelineRunner(lambda: run_pipeline(args.repo))
    ok = runner.run()
    
    if args.batch:
        print(f" DEBUG - Batch mode: exiting with 0")
        sys.exit(0)  # Always exit 0 in batch mode
    else:
        print(f" DEBUG - Interactive mode: exiting with {0 if ok else 1}")
        sys.exit(0 if ok else 1)