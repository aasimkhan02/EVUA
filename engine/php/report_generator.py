from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jinja2 import Template
from pydantic import BaseModel


class MetadataModel(BaseModel):
    source_version: str
    target_version: str
    timestamp: str
    files_analyzed: int
    total_issues: int


class SummaryModel(BaseModel):
    automatable_changes: int
    manual_review_items: int
    risk_level: str
    estimated_effort_hours: float


class ReportModel(BaseModel):
    metadata: MetadataModel
    summary: SummaryModel
    files: list[dict[str, Any]]
    changes_by_category: dict[str, int]
    ai_handoff_summary: dict[str, Any]
    migration_path: list[dict[str, Any]]


def build_report(data: dict[str, Any]) -> ReportModel:
    return ReportModel.model_validate(data)


def render_json(report: ReportModel) -> str:
    return json.dumps(report.model_dump(), indent=2)


def render_markdown(report: ReportModel) -> str:
    d = report.model_dump()
    lines = [
        "# EVUA Migration Report",
        "",
        f"- Source version: {d['metadata']['source_version']}",
        f"- Target version: {d['metadata']['target_version']}",
        f"- Files analyzed: {d['metadata']['files_analyzed']}",
        f"- Total issues: {d['metadata']['total_issues']}",
        f"- Risk level: {d['summary']['risk_level']}",
        "",
        "## Changes by Category",
    ]
    for key, value in d["changes_by_category"].items():
        lines.append(f"- {key}: {value}")

    lines.append("")
    lines.append("## Files")
    for item in d["files"]:
        lines.append(f"### {item['path']}")
        lines.append(f"- Risk score: {item['risk_score']}")
        lines.append(f"- Changes: {len(item.get('changes', []))}")
        lines.append(f"- AI handoff needed: {item.get('ai_handoff', {}).get('needed', False)}")
        lines.append("")

    return "\n".join(lines)


def render_html(report: ReportModel) -> str:
    template = Template(
        """
<!doctype html>
<html>
<head>
  <meta charset=\"utf-8\">
  <title>EVUA Migration Report</title>
  <style>
    :root { --bg:#f7f7f3; --ink:#1d1f21; --accent:#0b6e4f; --warn:#b44c2b; }
    body { font-family: Georgia, 'Times New Roman', serif; margin: 24px; background: radial-gradient(circle at top, #fff, var(--bg)); color: var(--ink); }
    .card { background:#fff; border:1px solid #ded7cf; border-radius:12px; padding:16px; margin-bottom:16px; }
    .grid { display:grid; grid-template-columns: repeat(auto-fit,minmax(220px,1fr)); gap:12px; }
    .pill { display:inline-block; padding:2px 8px; border-radius:999px; background:#eef7f3; color:var(--accent); }
    table { width:100%; border-collapse: collapse; }
    td,th { border-bottom:1px solid #ece7e1; padding:8px; text-align:left; }
    .risk-high { color: var(--warn); font-weight: bold; }
  </style>
</head>
<body>
  <h1>EVUA Migration Report</h1>
  <div class=\"card grid\">
    <div><strong>Source</strong><br>{{ r.metadata.source_version }}</div>
    <div><strong>Target</strong><br>{{ r.metadata.target_version }}</div>
    <div><strong>Files</strong><br>{{ r.metadata.files_analyzed }}</div>
    <div><strong>Issues</strong><br>{{ r.metadata.total_issues }}</div>
  </div>
  <div class=\"card\">
    <h2>Summary</h2>
    <p>Risk level: <span class=\"pill\">{{ r.summary.risk_level }}</span></p>
    <p>Automatable changes: {{ r.summary.automatable_changes }}</p>
    <p>Manual review items: {{ r.summary.manual_review_items }}</p>
    <p>Estimated effort: {{ r.summary.estimated_effort_hours }} hours</p>
  </div>
  <div class=\"card\">
    <h2>Files</h2>
    <table>
      <thead><tr><th>Path</th><th>Risk score</th><th>Changes</th><th>AI needed</th></tr></thead>
      <tbody>
        {% for f in r.files %}
        <tr>
          <td>{{ f.path }}</td>
          <td class=\"{% if f.risk_score >= 0.7 %}risk-high{% endif %}\">{{ f.risk_score }}</td>
          <td>{{ f.changes|length }}</td>
          <td>{{ f.ai_handoff.needed }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</body>
</html>
        """
    )
    return template.render(r=report.model_dump())


def write_report(report: ReportModel, output_path: str, fmt: str) -> str:
    path = Path(output_path)

    # Decide filename based on format
    ext_map = {
        "json": "json",
        "html": "html",
        "markdown": "md",
    }

    if fmt not in ext_map:
        raise ValueError(f"Unsupported report format: {fmt}")

    # If path is a directory OR has no suffix → treat as folder
    if path.exists() and path.is_dir() or path.suffix == "":
        path.mkdir(parents=True, exist_ok=True)
        file_path = path / f"evua_report.{ext_map[fmt]}"
    else:
        # It's already a file path
        path.parent.mkdir(parents=True, exist_ok=True)
        file_path = path

    # Render content
    if fmt == "json":
        text = render_json(report)
    elif fmt == "html":
        text = render_html(report)
    elif fmt == "markdown":
        text = render_markdown(report)

    file_path.write_text(text, encoding="utf-8")
    return str(file_path)


def default_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
