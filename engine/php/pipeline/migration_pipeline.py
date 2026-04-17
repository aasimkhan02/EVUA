"""
Migration Pipeline
Orchestrates: file scanning → AST parsing → rule engine → AI processor.
"""
import asyncio
import logging
import os
import uuid
from pathlib import Path
from typing import Optional, Union

from ..ast_parser import PHPASTParser
from ..rule_engine import RuleEngine
from ..ai_processor import GeminiProcessor, MockAIProcessor
from ..models.migration_models import (
    FileContext,
    MigrationResult,
    MigrationStatus,
    PHPVersion,
    PipelineResult,
)
from ..utils.file_scanner import FileScanner
from ..utils.diff_generator import generate_diff

logger = logging.getLogger("evua.pipeline")


class MigrationPipeline:
    """
    High-level pipeline for migrating a PHP project.

    Stages
    ------
    1. Scan   — discover all .php files
    2. Parse  — build AST for each file
    3. Rules  — apply rule-based auto-fixes
    4. AI     — send AI-required issues to Gemini
    5. Output — write migrated files (optional) / return results
    """

    def __init__(
        self,
        source_version: PHPVersion,
        target_version: PHPVersion,
        gemini_api_key: Optional[str] = None,
        dry_run: bool = False,
        use_mock_ai: bool = False,
        max_concurrency: int = 5,
    ):
        self.source_version = source_version
        self.target_version = target_version
        self.dry_run = dry_run
        self.max_concurrency = max_concurrency

        self.rule_engine = RuleEngine(dry_run=dry_run)
        self.scanner = FileScanner()

        if use_mock_ai or not gemini_api_key:
            self.ai_processor: Union[GeminiProcessor, MockAIProcessor] = MockAIProcessor()
            if not use_mock_ai:
                logger.warning("No Gemini API key — using mock AI processor")
        else:
            self.ai_processor = GeminiProcessor(api_key=gemini_api_key)

    # ---------------------------------------------------------------------- public

    def run_file(self, file_path: str) -> MigrationResult:
        """Synchronously migrate a single PHP file."""
        return asyncio.get_event_loop().run_until_complete(
            self._process_file(file_path)
        )

    def run_directory(
        self, directory: str, output_dir: Optional[str] = None
    ) -> PipelineResult:
        """Synchronously migrate all PHP files in a directory."""
        return asyncio.get_event_loop().run_until_complete(
            self._run_directory_async(directory, output_dir)
        )

    async def run_file_async(self, file_path: str) -> MigrationResult:
        return await self._process_file(file_path)

    async def run_directory_async(
        self, directory: str, output_dir: Optional[str] = None
    ) -> PipelineResult:
        return await self._run_directory_async(directory, output_dir)

    # ---------------------------------------------------------------------- internals

    async def _run_directory_async(
        self, directory: str, output_dir: Optional[str]
    ) -> PipelineResult:
        files = self.scanner.scan(directory)
        job_id = str(uuid.uuid4())

        pipeline_result = PipelineResult(
            job_id=job_id,
            source_version=self.source_version,
            target_version=self.target_version,
            total_files=len(files),
        )

        semaphore = asyncio.Semaphore(self.max_concurrency)

        async def bounded(fp: str) -> MigrationResult:
            async with semaphore:
                return await self._process_file(fp)

        tasks = [bounded(fp) for fp in files]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for fp, res in zip(files, results):
            if isinstance(res, Exception):
                logger.error("Pipeline error for %s: %s", fp, res)
                pipeline_result.failed += 1
                pipeline_result.results.append(
                    MigrationResult(
                        file_path=fp,
                        original_code="",
                        migrated_code="",
                        status=MigrationStatus.FAILED,
                        errors=[str(res)],
                    )
                )
            else:
                pipeline_result.results.append(res)
                if res.status == MigrationStatus.FAILED:
                    pipeline_result.failed += 1
                elif res.status == MigrationStatus.SKIPPED:
                    pipeline_result.skipped += 1
                else:
                    pipeline_result.completed += 1

                if output_dir and not self.dry_run:
                    self._write_output(fp, directory, output_dir, res.migrated_code)

        pipeline_result.summary = self._summarise(pipeline_result)
        return pipeline_result

    async def _process_file(self, file_path: str) -> MigrationResult:
        """Full pipeline for a single file."""
        logger.info("Processing: %s", file_path)

        # 1. Read source
        try:
            source = Path(file_path).read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            return MigrationResult(
                file_path=file_path,
                original_code="",
                migrated_code="",
                status=MigrationStatus.FAILED,
                errors=[f"Cannot read file: {exc}"],
            )

        # 2. Parse AST
        ast = None
        try:
            parser = PHPASTParser(source)
            ast = parser.parse()
        except Exception as exc:
            logger.warning("AST parse failed for %s: %s", file_path, exc)
            # Continue without AST — regex rules still work

        # 3. Rule engine
        result = self.rule_engine.run(
            file_path=file_path,
            source=source,
            ast=ast,
            source_version=self.source_version,
            target_version=self.target_version,
        )
        result.stats["ast_parsed"] = ast is not None

        # 4. AI processing (if needed)
        if result.status == MigrationStatus.AI_REQUIRED:
            result = await self.ai_processor.process(
                result=result,
                source_version=self.source_version,
                target_version=self.target_version,
            )
            result.stats["ast_parsed"] = ast is not None

        # 5. Attach diff for reporting
        result.stats["diff"] = generate_diff(
            source, result.migrated_code, file_path
        )

        return result

    @staticmethod
    def _write_output(
        original_path: str,
        base_dir: str,
        output_dir: str,
        content: str,
    ):
        rel = os.path.relpath(original_path, base_dir)
        out_path = os.path.join(output_dir, rel)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        Path(out_path).write_text(content, encoding="utf-8")
        logger.debug("Written: %s", out_path)

    @staticmethod
    def _summarise(pipeline_result: PipelineResult) -> dict:
        all_issues = [
            issue
            for r in pipeline_result.results
            for issue in r.issues
        ]
        sev_totals: dict = {}
        for issue in all_issues:
            sev_totals[issue.severity] = sev_totals.get(issue.severity, 0) + 1

        return {
            "total_files": pipeline_result.total_files,
            "completed": pipeline_result.completed,
            "failed": pipeline_result.failed,
            "skipped": pipeline_result.skipped,
            "total_issues": len(all_issues),
            "ai_fixes_applied": sum(
                len(r.ai_changes) for r in pipeline_result.results
            ),
            "rule_fixes_applied": sum(
                r.stats.get("auto_fixable", 0) for r in pipeline_result.results
            ),
            "severity_breakdown": sev_totals,
        }
