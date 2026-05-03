from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Optional

import requests

from ..models.migration_models import (
    MigrationIssue,
    MigrationResult,
    MigrationStatus,
    PHPVersion,
)

logger = logging.getLogger("evua.ai_processor")

OLLAMA_MODEL = "gemma3:latest"
OLLAMA_API_BASE = "http://localhost:11434"


SYSTEM_PROMPT = """You are an expert PHP developer specialising in version migrations.
Your task is to migrate PHP code from one version to another, fixing all identified issues.

You will receive:
1. The PHP source code (potentially partially migrated by automated rules)
2. A list of issues that still need to be addressed
3. The source and target PHP versions

Rules:
- Return ONLY valid PHP code — no markdown fences, no explanation outside the code
- Preserve all logic, comments, and functionality
- Apply only the changes necessary to fix listed issues
- Prefer modern PHP idioms appropriate for the target version
- If a change is ambiguous or risky, add a // EVUA: review comment near that line
- Return a JSON object with keys: "migrated_code" and "changes" (array of change descriptions)
"""


class OllamaProcessor:
    """Calls a local Ollama server to apply AI-driven migration fixes."""

    def __init__(self, api_base: str = OLLAMA_API_BASE, model: str = OLLAMA_MODEL, timeout: int = 120):
        self.api_base = api_base.rstrip("/")
        self.model = model
        self.timeout = timeout

    async def process(
        self,
        result: MigrationResult,
        source_version: PHPVersion,
        target_version: PHPVersion,
        additional_context: Optional[str] = None,
    ) -> MigrationResult:
        ai_issues = [i for i in result.issues if i.requires_ai]
        if not ai_issues:
            result.status = MigrationStatus.COMPLETED
            return result

        prompt = self._build_prompt(
            code=result.migrated_code,
            issues=ai_issues,
            source_version=source_version,
            target_version=target_version,
            context=additional_context,
        )

        try:
            response_text = await asyncio.to_thread(self._call_ollama, prompt)
            migrated_code, changes = self._parse_response(response_text, result.migrated_code)

            result.migrated_code = migrated_code
            result.ai_changes = changes
            result.status = MigrationStatus.AI_APPLIED

        except Exception as exc:
            logger.error("Ollama API error for %s: %s", result.file_path, exc)
            result.errors.append(f"AI processing failed: {exc}")
            result.status = MigrationStatus.FAILED

        return result

    def _build_prompt(
        self,
        code: str,
        issues: list[MigrationIssue],
        source_version: PHPVersion,
        target_version: PHPVersion,
        context: Optional[str],
    ) -> str:
        issue_list = "\n".join(
            f"- [Line {i.line}] [{i.severity.upper()}] {i.rule_id}: {i.message}"
            + (f"\n  Code: {i.original_code[:120]}" if i.original_code else "")
            for i in issues
        )

        prompt = f"""Migrate the following PHP code from PHP {source_version.value} to PHP {target_version.value}.

## Issues to fix
{issue_list}
"""
        if context:
            prompt += f"\n## Additional context\n{context}\n"

        prompt += f"""
## PHP Source Code
```php
{code}
```

Respond with ONLY a JSON object in this exact format (no markdown fences around the JSON):
{{
  "migrated_code": "<complete migrated PHP code here>",
  "changes": [
    "<description of change 1>",
    "<description of change 2>"
  ]
}}"""
        return prompt

    def _call_ollama(self, prompt: str) -> str:
        url = f"{self.api_base}/api/generate"
        payload = {
            "model": self.model,
            "prompt": f"{SYSTEM_PROMPT}\n\n{prompt}",
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.1,
            },
        }

        response = requests.post(url, json=payload, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        response_text = data.get("response", "")
        if not response_text:
            raise ValueError("Ollama returned an empty response")

        return response_text

    def _parse_response(self, response_text: str, fallback_code: str) -> tuple[str, list[dict]]:
        cleaned = re.sub(r"^```(?:json)?\s*", "", response_text.strip())
        cleaned = re.sub(r"\s*```$", "", cleaned)

        try:
            data = json.loads(cleaned)
            migrated_code = data.get("migrated_code", fallback_code)
            changes = data.get("changes", [])

            if "<?php" not in migrated_code and "<?=" not in migrated_code:
                logger.warning("AI response missing PHP open tag, using fallback")
                return fallback_code, []

            return migrated_code, [{"description": c} for c in changes]

        except json.JSONDecodeError as exc:
            logger.error("Failed to parse Ollama JSON response: %s", exc)
            logger.debug("Raw response: %s", response_text[:500])
            return fallback_code, []