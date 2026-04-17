import json
from pathlib import Path


def write_json_report(name, report, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{name}.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")


def write_markdown_report(name, report, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{name}.md"

    m = report["metrics"]

    md = f"# Benchmark: {name}\n\n"
    md += f"Validation Passed: {'✅' if report['validation_passed'] else '❌'}\n\n"

    md += "## Coverage\n"
    md += f"- Auto-modernization coverage: {m['auto_coverage']:.2f}\n"
    md += f"- Manual detection recall: {m['manual_recall']:.2f}\n"
    md += f"- File accuracy: {m['file_accuracy']:.2f}\n\n"

    md += "## Risk Classification\n"
    md += "| Risk | Precision | Recall |\n"
    md += "|------|-----------|--------|\n"

    for level, stats in m["risk"].items():
        md += f"| {level} | {stats['precision']:.2f} | {stats['recall']:.2f} |\n"

    md += "\n## CI Gates\n"
    md += f"- Meets min auto coverage: {'✅' if m['meets_min_auto_coverage'] else '❌'}\n"
    md += f"- Meets manual ratio: {'✅' if m['meets_manual_ratio'] else '❌'}\n"
    md += f"- Validation expected: {'✅' if m['validation_passed'] == m['validation_expected'] else '❌'}\n"

    path.write_text(md, encoding="utf-8")
