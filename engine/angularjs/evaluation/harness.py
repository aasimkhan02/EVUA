from pathlib import Path
import json
import pprint

from evaluation.config import BENCHMARKS_ROOT, REPORTS_ROOT
from evaluation.schemas import load_expected
from evaluation.runners import run_pipeline_on_repo
from evaluation.metrics import compute_metrics
from evaluation.reporters import write_json_report, write_markdown_report


def _adapt_evua_report(evua_report: dict, benchmark_name: str) -> dict:
    """Convert EVUA's report format to benchmark expected format with extensive debugging."""
    
    print(f"\n   DEBUG [{benchmark_name}] - Starting _adapt_evua_report")
    print(f"   DEBUG - Report type: {type(evua_report)}")
    print(f"   DEBUG - Report keys: {list(evua_report.keys())}")
    
    # Check if report is empty
    if not evua_report:
        print(f"   DEBUG - Report is EMPTY!")
        return {
            "risk": {"SAFE": [], "RISKY": [], "MANUAL": []},
            "generated_files": [],
            "auto_modernized": [],
            "manual_required": [],
            "validation_passed": False,
        }
    
    # Check changes array
    changes = evua_report.get("changes", [])
    print(f"   DEBUG - changes array type: {type(changes)}")
    print(f"   DEBUG - changes array length: {len(changes)}")
    
    if changes:
        print(f"   DEBUG - First change item type: {type(changes[0]) if changes else 'N/A'}")
        print(f"   DEBUG - First change keys: {list(changes[0].keys()) if changes else 'N/A'}")
        print(f"   DEBUG - First change sample: {json.dumps(changes[0], indent=2)[:200]}...")
    else:
        print(f"    DEBUG - changes array is empty")
        # Dump the hole report structure for debugging
        print(f"   DEBUG - Full report structure:")
        pprint.pprint(evua_report, indent=2, width=100)
    
    risk_by_level = evua_report.get("risk", {}).get("by_level", {})
    transformation = evua_report.get("transformation", {})
    validation = evua_report.get("validation", {})
    
    print(f"   DEBUG - risk_by_level: {risk_by_level}")
    print(f"   DEBUG - transformation keys: {list(transformation.keys())}")
    print(f"   DEBUG - validation: {validation}")
    
    # Handle empty changes array gracefully
    if not changes:
        print(f"    DEBUG - No changes detected - returning minimal structure")
        return {
            "risk": {
                "SAFE": risk_by_level.get("SAFE", []),
                "RISKY": risk_by_level.get("RISKY", []),
                "MANUAL": risk_by_level.get("MANUAL", []),
            },
            "generated_files": transformation.get("generated_files", []),
            "auto_modernized": transformation.get("auto_modernized", []),
            "manual_required": transformation.get("manual_required", []),
            "validation_passed": bool(validation.get("tests_passed")) and bool(validation.get("snapshot_passed")),
        }

    def _looks_like_uuid(s: str) -> bool:
        if not isinstance(s, str):
            return False
        parts = s.split("-")
        return len(parts) == 5 and all(len(p) in (8, 4, 4, 4, 12) for p in parts)

    def _best_name(change: dict) -> str:
        name = change.get("before_name", "")
        if name and name != "unknown":
            return name
        bid = change.get("before_id", "")
        if bid and not _looks_like_uuid(bid):
            return bid
        return ""

    safe_names, risky_names, manual_names = set(), set(), set()
    for i, c in enumerate(changes):
        name = _best_name(c)
        print(f"   DEBUG - Change {i}: name='{name}', risk={c.get('risk', 'unknown')}")
        if not name:
            continue
        risk_str = str(c.get("risk", "")).upper()
        if "MANUAL" in risk_str:
            manual_names.add(name)
        elif "RISKY" in risk_str:
            risky_names.add(name)
        else:
            safe_names.add(name)

    def _has_names(lst):
        return lst and any(not _looks_like_uuid(x) for x in lst)

    if _has_names(risk_by_level.get("SAFE", [])):
        safe_names = set(risk_by_level["SAFE"])
        print(f"   DEBUG - Overriding safe_names from risk_by_level: {safe_names}")
    if _has_names(risk_by_level.get("RISKY", [])):
        risky_names = set(risk_by_level["RISKY"])
        print(f"   DEBUG - Overriding risky_names from risk_by_level: {risky_names}")
    if _has_names(risk_by_level.get("MANUAL", [])):
        manual_names = set(risk_by_level["MANUAL"])
        print(f"   DEBUG - Overriding manual_names from risk_by_level: {manual_names}")

    raw_auto = transformation.get("auto_modernized", [])
    raw_manual = transformation.get("manual_required", [])

    print(f"   DEBUG - raw_auto from transformation: {raw_auto}")
    print(f"   DEBUG - raw_manual from transformation: {raw_manual}")

    auto_modernized = raw_auto if _has_names(raw_auto) else sorted(safe_names | risky_names)
    manual_required = raw_manual if _has_names(raw_manual) else sorted(manual_names)

    generated_files = transformation.get("generated_files") or [
        c.get("output_path") for c in changes if c.get("output_path")
    ]

    validation_passed = bool(validation.get("tests_passed")) and bool(validation.get("snapshot_passed"))

    result = {
        "risk": {
            "SAFE": sorted(safe_names),
            "RISKY": sorted(risky_names),
            "MANUAL": sorted(manual_names),
        },
        "generated_files": generated_files,
        "auto_modernized": auto_modernized,
        "manual_required": manual_required,
        "validation_passed": validation_passed,
    }
    
    print(f"   DEBUG - Final result: {json.dumps(result, indent=2)[:500]}...")
    return result


def run_all_benchmarks():
    REPORTS_ROOT.mkdir(exist_ok=True)
    summary = []

    bench_dirs = sorted([d for d in BENCHMARKS_ROOT.iterdir() if d.is_dir()])

    if not bench_dirs:
        print(f"No benchmark directories found under {BENCHMARKS_ROOT}")
        return summary

    for bench_dir in bench_dirs:
        name = bench_dir.name
        repo_path = bench_dir / "repo"

        print(f"\n{'='*55}")
        print(f"  Benchmark: {name}")
        print(f"{'='*55}")

        # Check if repo directory exists
        if not repo_path.exists():
            print(f"   ERROR: repo path does not exist: {repo_path}")
            continue

        try:
            expected = load_expected(bench_dir)
            print(f"   Loaded expected data for {name}")
        except Exception as e:
            print(f"   ERROR loading expected files: {e}")
            continue

        print(f"   Running pipeline on: {repo_path}")
        result = run_pipeline_on_repo(repo_path)
        print(f"   Pipeline completed with return code: {result['returncode']}")

        report_path = repo_path / ".evua_report.json"
        print(f"   Looking for report at: {report_path}")

        # Check if report exists
        if not report_path.exists():
            print(f"   ERROR: EVUA report not written at {report_path}")
            
            # Check parent directory for stale reports
            alt = bench_dir / ".evua_report.json"
            if alt.exists():
                print(f"    Found stale report at {alt}")
                print(f"   Stale report size: {alt.stat().st_size} bytes")
                # Show first few lines of stale report
                try:
                    stale_content = alt.read_text(encoding="utf-8")[:500]
                    print(f"   Stale report preview: {stale_content}")
                except:
                    pass
            
            print(f"   STDOUT (last 2000 chars):")
            print(result["stdout"][-2000:])
            print(f"   STDERR (last 1000 chars):")
            print(result["stderr"][-1000:])
            
            summary.append({"benchmark": name, "error": "no report written"})
            continue

        # Report exists, read it
        report_size = report_path.stat().st_size
        print(f"   Report found at {report_path} (size: {report_size} bytes)")
        
        try:
            report_content = report_path.read_text(encoding="utf-8")
            print(f"   Report preview (first 500 chars): {report_content[:500]}")
            
            evua_report = json.loads(report_content)
            print(f"   Successfully parsed JSON report")
            
        except json.JSONDecodeError as e:
            print(f"   ERROR: Failed to parse JSON report: {e}")
            print(f"   Raw content (first 500 chars): {report_content[:500]}")
            summary.append({"benchmark": name, "error": "invalid JSON"})
            continue
        except Exception as e:
            print(f"   ERROR: Failed to read report: {e}")
            summary.append({"benchmark": name, "error": str(e)})
            continue

        # Adapt the report
        print(f"   Adapting report...")
        actual = _adapt_evua_report(evua_report, name)
        
        # Compute metrics
        print(f"   Computing metrics...")
        metrics = compute_metrics(actual, expected)

        # Debug: show what names were resolved
        print(f"   RESULTS:")
        print(f"    auto_modernized : {actual['auto_modernized']}")
        print(f"    manual_required : {actual['manual_required']}")
        print(f"    expected_auto   : {expected['auto_modernized']}")
        print(f"    expected_manual : {expected['manual_required']}")
        print(f"    risk SAFE       : {actual['risk']['SAFE']}")
        print(f"    risk RISKY      : {actual['risk']['RISKY']}")
        print(f"    risk MANUAL     : {actual['risk']['MANUAL']}")

        report = {
            "benchmark": name,
            "metrics": metrics,
            "validation_passed": actual["validation_passed"],
            "raw_returncode": result["returncode"],
        }

        # Write reports
        write_json_report(name, report, REPORTS_ROOT)
        write_markdown_report(name, report, REPORTS_ROOT)

        print(f"   METRICS:")
        print(f"    auto_coverage : {metrics['auto_coverage']:.2f}")
        print(f"    manual_recall : {metrics['manual_recall']:.2f}")
        print(f"    file_accuracy : {metrics['file_accuracy']:.2f}")
        print(f"    validation    : {actual['validation_passed']}")

        summary.append(report)

    print(f"\n{'='*55}")
    print(f"  Done. {len(summary)} benchmarks evaluated.")
    print(f"  Reports at: {REPORTS_ROOT}")
    
    # Print summary of errors if any
    errors = [s for s in summary if "error" in s]
    if errors:
        print(f"\n   Errors encountered:")
        for e in errors:
            print(f"    - {e['benchmark']}: {e['error']}")
    
    return summary


if __name__ == "__main__":
    run_all_benchmarks()