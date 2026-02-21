from pathlib import Path
import json

from evaluation.config import BENCHMARKS_ROOT, REPORTS_ROOT
from evaluation.schemas import load_expected
from evaluation.runners import run_pipeline_on_repo
from evaluation.metrics import compute_metrics
from evaluation.reporters import write_json_report, write_markdown_report


def _adapt_evua_report(evua_report: dict) -> dict:
    """
    Maps EVUA's real JSON report schema → evaluation harness schema.

    Real report structure (from cli.py):
    {
      "changes": [
        { "before_id": "...", "risk": "RiskLevel.SAFE", "output_path": "..." }
      ],
      "risk": {
        "by_level": { "SAFE": [...], "RISKY": [...], "MANUAL": [...] }
      },
      "transformation": {
        "generated_files": [...],
        "auto_modernized": [...],
        "manual_required": [...]
      },
      "validation": { "tests_passed": bool, "snapshot_passed": bool }
    }
    """
    # Top-level harness-friendly fields (written by cli.py)
    risk_by_level  = evua_report.get("risk", {}).get("by_level", {})
    transformation = evua_report.get("transformation", {})
    validation     = evua_report.get("validation", {})

    # Fallback: if by_level is missing, reconstruct from the flat changes list
    if not any(risk_by_level.values()):
        safe, risky, manual = [], [], []
        for change in evua_report.get("changes", []):
            risk_str  = str(change.get("risk", "")).upper()
            before_id = change.get("before_id", "")
            if "MANUAL" in risk_str:
                manual.append(before_id)
            elif "RISKY" in risk_str:
                risky.append(before_id)
            else:
                safe.append(before_id)
        risk_by_level = {"SAFE": safe, "RISKY": risky, "MANUAL": manual}

    # Fallback: reconstruct generated_files / auto_modernized / manual_required
    generated_files = transformation.get("generated_files") or [
        c.get("output_path") for c in evua_report.get("changes", [])
        if c.get("output_path")
    ]
    auto_modernized = transformation.get("auto_modernized") or [
        c.get("before_id") for c in evua_report.get("changes", [])
        if "MANUAL" not in str(c.get("risk", "")).upper()
    ]
    manual_required = transformation.get("manual_required") or risk_by_level.get("MANUAL", [])

    validation_passed = (
        bool(validation.get("tests_passed")) and
        bool(validation.get("snapshot_passed"))
    )

    return {
        "risk": {
            "SAFE":   risk_by_level.get("SAFE",   []),
            "RISKY":  risk_by_level.get("RISKY",  []),
            "MANUAL": risk_by_level.get("MANUAL", []),
        },
        "generated_files": generated_files,
        "auto_modernized": auto_modernized,
        "manual_required": manual_required,
        "validation_passed": validation_passed,
    }


def run_all_benchmarks():
    REPORTS_ROOT.mkdir(exist_ok=True)
    summary = []

    bench_dirs = sorted(
        [d for d in BENCHMARKS_ROOT.iterdir() if d.is_dir()]
    )

    if not bench_dirs:
        print(f"No benchmark directories found under {BENCHMARKS_ROOT}")
        return summary

    for bench_dir in bench_dirs:
        name      = bench_dir.name
        repo_path = bench_dir / "repo"

        print(f"\n{'='*55}")
        print(f"  Benchmark: {name}")
        print(f"{'='*55}")

        try:
            expected = load_expected(bench_dir)
        except Exception as e:
            print(f"  ERROR loading expected files: {e}")
            continue

        result     = run_pipeline_on_repo(repo_path)
        report_path = repo_path / ".evua_report.json"

        if not report_path.exists():
            print(f"  ERROR: EVUA report not written at {report_path}")
            print("  STDOUT:", result["stdout"][-1000:])
            print("  STDERR:", result["stderr"][-1000:])
            summary.append({"benchmark": name, "error": "no report written"})
            continue

        evua_report = json.loads(report_path.read_text(encoding="utf-8"))
        actual      = _adapt_evua_report(evua_report)
        metrics     = compute_metrics(actual, expected)

        report = {
            "benchmark":        name,
            "metrics":          metrics,
            "validation_passed": actual["validation_passed"],
            "raw_returncode":   result["returncode"],
        }

        write_json_report(name, report, REPORTS_ROOT)
        write_markdown_report(name, report, REPORTS_ROOT)

        print(f"  auto_coverage : {metrics['auto_coverage']:.2f}")
        print(f"  manual_recall : {metrics['manual_recall']:.2f}")
        print(f"  file_accuracy : {metrics['file_accuracy']:.2f}")
        print(f"  validation    : {actual['validation_passed']}")

        summary.append(report)

    print(f"\n{'='*55}")
    print(f"  Done. {len(summary)} benchmarks evaluated.")
    print(f"  Reports at: {REPORTS_ROOT}")
    return summary


if __name__ == "__main__":
    run_all_benchmarks()