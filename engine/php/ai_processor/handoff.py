from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests


@dataclass
class AIUsage:
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    processed: int = 0
    successful: int = 0
    failed: int = 0


class GeminiHandoffProcessor:
    def __init__(
        self,
        api_key: str | None,
        model: str,
        cache_dir: str = ".evua/ai_cache",
        mock_mode: bool = False,
        cache_responses: bool = True,
    ):
        self.api_key = api_key
        self.model = model
        self.mock_mode = mock_mode
        self.cache_responses = cache_responses
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _hash_payload(payload: dict[str, Any]) -> str:
        raw = json.dumps(payload, sort_keys=True).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def _cache_file(self, key: str) -> Path:
        return self.cache_dir / f"{key}.json"

    def _build_prompt(self, item: dict[str, Any], source_version: str, target_version: str) -> str:
        snippet = (item.get("code_snippet") or "")[:1000]
        return (
            "You are a PHP migration specialist. Return only JSON with keys: suggestion, confidence, explanation.\n"
            f"Source version: {source_version}\n"
            f"Target version: {target_version}\n"
            f"Reason for review: {item.get('concern', 'complex migration case')}\n"
            f"Item description: {item.get('description', '')}\n"
            f"Code:\n{snippet}\n"
        )

    def _mock_response(self, item: dict[str, Any]) -> dict[str, Any]:
        return {
            "suggestion": "Review dynamic behavior and replace with explicit typed flow where possible.",
            "confidence": 0.73,
            "explanation": f"Mock analysis for {item.get('id', 'unknown')}.",
        }

    def _call_gemini_sdk(self, prompt: str) -> tuple[dict[str, Any], int]:
        import google.generativeai as genai

        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY is required for real AI mode")

        genai.configure(api_key=self.api_key)
        model = genai.GenerativeModel(self.model)
        response = model.generate_content(prompt)
        text = getattr(response, "text", "") or "{}"
        usage = getattr(response, "usage_metadata", None)
        tokens = int(getattr(usage, "total_token_count", 0) or 0)
        data = json.loads(text)
        return data, tokens

    def _call_gemini_rest(self, prompt: str) -> tuple[dict[str, Any], int]:
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY is required for real AI mode")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"},
        }
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        body = response.json()
        candidate = body["candidates"][0]["content"]["parts"][0]["text"]
        usage = body.get("usageMetadata", {})
        tokens = int(usage.get("totalTokenCount", 0) or 0)
        return json.loads(candidate), tokens

    def process_batch(
        self,
        items: list[dict[str, Any]],
        source_version: str,
        target_version: str,
    ) -> tuple[list[dict[str, Any]], AIUsage]:
        usage = AIUsage(processed=len(items))
        outputs: list[dict[str, Any]] = []

        for item in items:
            payload = {
                "item": item,
                "source_version": source_version,
                "target_version": target_version,
                "model": self.model,
            }
            key = self._hash_payload(payload)
            cache_file = self._cache_file(key)

            if self.cache_responses and cache_file.exists():
                cached = json.loads(cache_file.read_text(encoding="utf-8"))
                outputs.append(cached)
                usage.successful += 1
                usage.total_tokens += int(cached.get("token_usage", 0))
                continue

            try:
                if self.mock_mode:
                    data = self._mock_response(item)
                    tokens = 0
                else:
                    prompt = self._build_prompt(item, source_version, target_version)
                    try:
                        data, tokens = self._call_gemini_sdk(prompt)
                    except Exception:
                        data, tokens = self._call_gemini_rest(prompt)

                result = {
                    "id": item.get("id"),
                    "suggestion": data.get("suggestion"),
                    "confidence": float(data.get("confidence", 0.5)),
                    "explanation": data.get("explanation", ""),
                    "token_usage": tokens,
                }
                if self.cache_responses:
                    cache_file.write_text(json.dumps(result, indent=2), encoding="utf-8")

                outputs.append(result)
                usage.successful += 1
                usage.total_tokens += tokens

            except Exception as exc:
                outputs.append(
                    {
                        "id": item.get("id"),
                        "suggestion": None,
                        "confidence": 0.0,
                        "explanation": str(exc),
                        "token_usage": 0,
                        "error": True,
                    }
                )
                usage.failed += 1

        usage.estimated_cost_usd = round((usage.total_tokens / 1_000_000) * 2.5, 6)
        return outputs, usage
