"""
AI Processor — Gemini API
Handles complex migration changes that rule-based analysis can't auto-fix.
"""
import json
import logging
import re
from typing import Optional

try:
    import httpx
    _HTTPX_AVAILABLE = True
except ImportError:
    _HTTPX_AVAILABLE = False

from ..models.migration_models import (
    MigrationResult,
    MigrationIssue,
    MigrationStatus,
    PHPVersion,
    IssueSeverity,
)

logger = logging.getLogger("evua.ai_processor")

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"
GEMINI_MODEL = "gemini-1.5-pro"


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


class GeminiProcessor:
    """
    Calls the Gemini API to apply AI-driven migration fixes.
    Accepts a partially-migrated MigrationResult and returns an updated one.
    """

    def __init__(self, api_key: str, model: str = GEMINI_MODEL, timeout: int = 120):
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    async def process(
        self,
        result: MigrationResult,
        source_version: PHPVersion,
        target_version: PHPVersion,
        additional_context: Optional[str] = None,
    ) -> MigrationResult:
        """
        Send migrated_code + remaining AI-required issues to Gemini.
        Returns updated MigrationResult with ai_changes populated.
        """
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
            response_text = await self._call_gemini(prompt)
            migrated_code, changes = self._parse_response(response_text, result.migrated_code)

            result.migrated_code = migrated_code
            result.ai_changes = changes
            result.status = MigrationStatus.AI_APPLIED

        except Exception as exc:
            logger.error("Gemini API error for %s: %s", result.file_path, exc)
            result.errors.append(f"AI processing failed: {exc}")
            result.status = MigrationStatus.FAILED

        return result

    # ------------------------------------------------------------------ prompt

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

    # ------------------------------------------------------------------ API

    async def _call_gemini(self, prompt: str) -> str:
        url = (
            f"{GEMINI_API_BASE}/models/{self.model}:generateContent"
            f"?key={self.api_key}"
        )
        payload = {
            "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 8192,
                "responseMimeType": "application/json",
            },
        }

        if not _HTTPX_AVAILABLE:
            raise RuntimeError("httpx is required for AI processing: pip install httpx")
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

        candidates = data.get("candidates", [])
        if not candidates:
            raise ValueError("Gemini returned no candidates")

        parts = candidates[0].get("content", {}).get("parts", [])
        if not parts:
            raise ValueError("Gemini returned empty parts")

        return parts[0].get("text", "")

    # ------------------------------------------------------------------ parse

    def _parse_response(
        self, response_text: str, fallback_code: str
    ) -> tuple[str, list[dict]]:
        """
        Parse Gemini JSON response into (migrated_code, changes).
        Falls back to original code on parse failure.
        """
        # Strip markdown fences if present despite instructions
        cleaned = re.sub(r"^```(?:json)?\s*", "", response_text.strip())
        cleaned = re.sub(r"\s*```$", "", cleaned)

        try:
            data = json.loads(cleaned)
            migrated_code = data.get("migrated_code", fallback_code)
            changes = data.get("changes", [])

            # Basic sanity: must contain <?php
            if "<?php" not in migrated_code and "<?=" not in migrated_code:
                logger.warning("AI response missing PHP open tag, using fallback")
                return fallback_code, []

            return migrated_code, [{"description": c} for c in changes]

        except json.JSONDecodeError as exc:
            logger.error("Failed to parse Gemini JSON response: %s", exc)
            logger.debug("Raw response: %s", response_text[:500])
            return fallback_code, []


class MockAIProcessor:
    """
    Drop-in replacement for GeminiProcessor in tests/dev environments.
    Applies simple heuristics without calling the API.
    """

    async def process(
        self,
        result: MigrationResult,
        source_version: PHPVersion,
        target_version: PHPVersion,
        additional_context: Optional[str] = None,
    ) -> MigrationResult:
        code = result.migrated_code
        changes = []

        for issue in result.issues:
            if not issue.requires_ai:
                continue

            if issue.rule_id == "PHP56_MYSQL_EXT":
                code, n = re.subn(
                    r"\bmysql_connect\s*\(",
                    "mysqli_connect(",
                    code,
                )
                if n:
                    changes.append({"description": f"Replaced {n} mysql_connect → mysqli_connect"})

                code, n = re.subn(
                    r"\bmysql_query\s*\(",
                    "mysqli_query($connection, ",
                    code,
                )
                if n:
                    changes.append({"description": f"Replaced {n} mysql_query → mysqli_query"})

            elif issue.rule_id == "PHP7X_CREATE_FUNCTION":
                code, n = re.subn(
                    r"create_function\s*\(\s*'([^']*)'\s*,\s*'([^']*)'\s*\)",
                    lambda m: f"function({m.group(1)}) {{ {m.group(2)} }}",
                    code,
                )
                if n:
                    changes.append({"description": f"Replaced {n} create_function → anonymous fn"})

        result.migrated_code = code
        result.ai_changes = changes
        result.status = (
            MigrationStatus.AI_APPLIED if changes else MigrationStatus.COMPLETED
        )
        return result
