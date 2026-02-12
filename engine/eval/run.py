import sys
from pathlib import Path
import subprocess
import csv
import json

# Ensure project root is on PYTHONPATH
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.reporting.metrics import Metrics

RESULTS_DIR = ROOT / "eval" / "results"
REPOS_FILE = ROOT / "eval" / "repos.txt"
CLI = ROOT / "cli.py"

RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def run_repo(repo_path: str):
    print(f"▶ Evaluating: {repo_path}")
    proc = subprocess.run(
        ["python", str(CLI), repo_path, "--batch"],
        cwd=str(ROOT),
        capture_output=True,
        text=True
    )

    report_path = ROOT / "report.json"
    if not report_path.exists():
        print("  ❌ No report.json generated")
        print(proc.stdout)
        print(proc.stderr)
        return None

    data = json.loads(report_path.read_text(encoding="utf-8"))

    metrics = Metrics.from_run(
        transformation=type("T", (), {"changes": data.get("changes", [])})(),
        risk_by_change={c["after_id"]: c["risk"] for c in data.get("changes", [])},
        validation=data.get("validation", {})
    )

    return {
        "repo": repo_path,
        "percent_auto_converted": metrics.percent_auto_converted,
        "risky_changes": metrics.risky_changes,
        "manual_changes": metrics.manual_changes,
        "test_pass_rate": metrics.test_pass_rate,
        "exit_code": proc.returncode,
    }


def main():
    if not REPOS_FILE.exists():
        print(f"❌ repos.txt not found at: {REPOS_FILE}")
        sys.exit(1)

    repos = [r.strip() for r in REPOS_FILE.read_text().splitlines() if r.strip()]
    if not repos:
        print("❌ repos.txt is empty")
        sys.exit(1)

    rows = []

    for repo in repos:
        result = run_repo(repo)
        if result:
            rows.append(result)

    if not rows:
        print("❌ No successful runs. Check errors above.")
        sys.exit(1)

    # Write CSV
    csv_path = RESULTS_DIR / "summary.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    # Write Markdown
    md_path = RESULTS_DIR / "summary.md"
    lines = [
        "# EVUA Evaluation Summary\n",
        "| Repo | % Auto | Risky | Manual | Test Pass Rate | Exit |",
        "|------|--------|-------|--------|----------------|------|"
    ]
    for r in rows:
        lines.append(
            f"| {r['repo']} | {r['percent_auto_converted']} | {r['risky_changes']} | "
            f"{r['manual_changes']} | {r['test_pass_rate']} | {r['exit_code']} |"
        )
    md_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"\n📊 Evaluation complete.")
    print(f"- CSV: {csv_path}")
    print(f"- Markdown: {md_path}")


if __name__ == "__main__":
    main()
