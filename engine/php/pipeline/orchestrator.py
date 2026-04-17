from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from ..ai_processor.handoff import GeminiHandoffProcessor
from ..ast_parser.analyzer import AnalysisFinding, analyze_php_source
from ..migration_detector import detect_migration_path, estimate_effort_hours
from ..models.migration_models import PHPVersion
from ..report_generator import ReportModel, build_report, default_timestamp
from ..rule_engine.engine import RuleEngine
from ..utils.file_scanner import FileScanner


def _risk_score(findings: list[AnalysisFinding], issues: list[Any], metrics: Any) -> float:
    severity_weight = {"critical": 1.0, "high": 0.75, "medium": 0.45, "low": 0.2, "info": 0.1}
    issue_factor = 0.0
    for issue in issues:
        issue_factor += severity_weight.get(getattr(issue.severity, "value", "info"), 0.1)

    complexity_factor = min(1.0, metrics.cyclomatic_complexity / 25.0)
    nesting_factor = min(1.0, metrics.nesting_depth / 8.0)
    dynamic_factor = min(1.0, len(findings) / 10.0)

    score = 0.45 * min(1.0, issue_factor / 6.0) + 0.25 * complexity_factor + 0.15 * nesting_factor + 0.15 * dynamic_factor
    return round(min(1.0, score), 2)


class CLIOrchestrator:
    def __init__(self, config: Any):
        self.config = config
        self.scanner = FileScanner()
        self.jobs_dir = Path(".evua/jobs")
        self.jobs_dir.mkdir(parents=True, exist_ok=True)

    def _make_ai_item(self, file_path: str, source: str, idx: int, reason: str, snippet: str) -> dict[str, Any]:
        return {
            "id": f"ai_{idx:04d}",
            "description": f"Manual migration review for {file_path}",
            "code_snippet": snippet[:1000],
            "concern": reason,
        }

    def _load_file(self, file_path: str) -> str:
        return Path(file_path).read_text(encoding="utf-8", errors="replace")

    def analyze_or_migrate(
        self,
        path: str,
        source_version: str,
        target_version: str,
        dry_run: bool,
        do_migrate: bool,
        progress_cb: Any | None = None,
    ) -> tuple[str, ReportModel, dict[str, Any]]:
        src_v = PHPVersion(source_version)
        tgt_v = PHPVersion(target_version)
        files = self.scanner.scan(path) if Path(path).is_dir() else [path]
        job_id = str(uuid.uuid4())

        rule_engine = RuleEngine(dry_run=dry_run or not do_migrate)
        use_mock = self.config.gemini.mock_mode or not bool(self.config.gemini.api_key)
        ai_processor = GeminiHandoffProcessor(
            api_key=self.config.gemini.api_key,
            model=self.config.gemini.model,
            cache_dir=".evua/ai_cache",
            mock_mode=use_mock,
            cache_responses=self.config.gemini.cache_responses,
        )

        report_files: list[dict[str, Any]] = []
        all_ai_items: list[dict[str, Any]] = []
        all_categories: dict[str, int] = {
            "deprecated_functions": 0,
            "type_system_changes": 0,
            "namespace_updates": 0,
            "error_handling": 0,
            "syntax_changes": 0,
        }

        issue_total = 0
        automatable_total = 0
        manual_total = 0

        for idx, file_path in enumerate(files, start=1):
            source = self._load_file(file_path)
            ast, findings, metrics = analyze_php_source(file_path, source)
            result = rule_engine.run(file_path, source, ast, src_v, tgt_v)

            if do_migrate and not (dry_run or self.config.migration.dry_run):
                Path(file_path).write_text(result.migrated_code, encoding="utf-8")

            issue_total += len(result.issues)
            automatable_total += len([i for i in result.issues if i.auto_fixable])
            manual_total += len([i for i in result.issues if i.requires_ai])

            file_changes = []
            ai_items = []

            for rm in result.rule_matches:
                category = "syntax_changes"
                rid = rm.rule_id.lower()
                if "mysql" in rid or "deprecated" in rid:
                    category = "deprecated_functions"
                elif "type" in rid or "union" in rid:
                    category = "type_system_changes"
                elif "namespace" in rid or "stringable" in rid:
                    category = "namespace_updates"
                elif "error" in rid:
                    category = "error_handling"
                all_categories[category] += 1

            lines = source.splitlines()
            for issue in result.issues:
                old_line = lines[issue.line - 1].strip() if 0 < issue.line <= len(lines) else issue.original_code
                file_changes.append(
                    {
                        "type": "deprecated_function" if "mysql" in issue.rule_id.lower() else "rule_match",
                        "line": issue.line,
                        "old_code": old_line[:200],
                        "suggested_new_code": issue.suggested_fix,
                        "automatable": issue.auto_fixable,
                        "confidence": 0.95 if issue.auto_fixable else 0.65,
                        "reason": issue.message,
                    }
                )
                if issue.requires_ai:
                    ai_items.append(
                        self._make_ai_item(file_path, source, len(all_ai_items) + len(ai_items) + 1, issue.message, old_line)
                    )

            for finding in findings:
                if finding.category in {"dynamic_code", "variable_function", "magic_method"}:
                    ai_items.append(
                        self._make_ai_item(file_path, source, len(all_ai_items) + len(ai_items) + 1, finding.reason, finding.snippet)
                    )

            all_ai_items.extend(ai_items)
            score = _risk_score(findings, result.issues, metrics)

            report_files.append(
                {
                    "path": file_path,
                    "risk_score": score,
                    "changes": file_changes,
                    "metrics": {
                        "cyclomatic_complexity": metrics.cyclomatic_complexity,
                        "lines_of_code": metrics.lines_of_code,
                        "nesting_depth": metrics.nesting_depth,
                        "dependencies": metrics.dependencies,
                        "test_coverage_estimate": metrics.test_coverage_estimate,
                    },
                    "manual_review": [
                        {
                            "line": f.line,
                            "snippet": f.snippet,
                            "reason": f.reason,
                            "confidence": f.confidence,
                        }
                        for f in findings
                    ],
                    "ai_handoff": {
                        "needed": bool(ai_items),
                        "items": ai_items,
                    },
                }
            )

            if progress_cb:
                progress_cb(idx, len(files), file_path)

        ai_results, ai_usage = ai_processor.process_batch(all_ai_items, source_version, target_version)
        ai_lookup = {item["id"]: item for item in ai_results}

        for f in report_files:
            enriched = []
            for item in f["ai_handoff"]["items"]:
                merged = {**item, "gemini_response": ai_lookup.get(item["id"])}
                enriched.append(merged)
            f["ai_handoff"]["items"] = enriched

        migration_steps = detect_migration_path(src_v, tgt_v)
        report_dict = {
            "metadata": {
                "source_version": source_version,
                "target_version": target_version,
                "timestamp": default_timestamp(),
                "files_analyzed": len(files),
                "total_issues": issue_total,
            },
            "summary": {
                "automatable_changes": automatable_total,
                "manual_review_items": manual_total,
                "risk_level": "HIGH" if any(f["risk_score"] >= 0.7 for f in report_files) else "MEDIUM",
                "estimated_effort_hours": estimate_effort_hours(issue_total, len(all_ai_items)),
            },
            "files": report_files,
            "changes_by_category": all_categories,
            "ai_handoff_summary": {
                "total_items": len(all_ai_items),
                "processed": ai_usage.processed,
                "successful": ai_usage.successful,
                "failed": ai_usage.failed,
                "total_tokens_used": ai_usage.total_tokens,
                "estimated_cost_usd": ai_usage.estimated_cost_usd,
            },
            "migration_path": [
                {
                    "step": i + 1,
                    "from": step.from_version.value,
                    "to": step.to_version.value,
                    "label": step.label,
                    "dependencies": [] if i == 0 else [migration_steps[i - 1].label],
                }
                for i, step in enumerate(migration_steps)
            ],
        }

        report = build_report(report_dict)
        artifact = {
            "job_id": job_id,
            "report": report.model_dump(),
        }
        (self.jobs_dir / f"{job_id}.json").write_text(json.dumps(artifact, indent=2), encoding="utf-8")

        return job_id, report, artifact

    def load_job_report(self, job_id: str) -> ReportModel:
        path = self.jobs_dir / f"{job_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"Unknown job id: {job_id}")

        payload = json.loads(path.read_text(encoding="utf-8"))
        return build_report(payload["report"])
