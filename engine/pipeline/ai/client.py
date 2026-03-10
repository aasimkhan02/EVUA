"""
pipeline/ai/client.py
=====================

Thin wrapper around LLM APIs for EVUA's AI-assist post-processing stage.

Provider priority
-----------------
1. Google Gemini  — free tier: gemini-2.0-flash
                    15 req/min, 1M tokens/day
                    Set env var: GEMINI_API_KEY

2. Groq           — free tier: llama-3.3-70b-versatile
                    30 req/min on free plan
                    Set env var: GROQ_API_KEY

3. Degraded mode  — if neither key is set, AIClient.complete() returns None
                    and the stage skips AI tasks gracefully.

Usage
-----
    from pipeline.ai.client import AIClient

    client = AIClient()
    result = client.complete("Write an Angular template for...")
    if result is None:
        # no API key available — skip
        pass

The client is stateless. Each call to complete() is independent.
No conversation history is maintained.
"""

import os
import json
import time
import urllib.request
import urllib.error
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

GEMINI_MODEL   = "gemini-2.0-flash"
GROQ_MODEL     = "llama-3.3-70b-versatile"

GEMINI_URL     = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)
GROQ_URL       = "https://api.groq.com/openai/v1/chat/completions"

# Conservative limits — stay well under free tier caps
MAX_OUTPUT_TOKENS = 1024
REQUEST_TIMEOUT   = 30   # seconds
MAX_RETRIES       = 2
RETRY_DELAY       = 5    # seconds between retries on rate-limit


# ─────────────────────────────────────────────────────────────────────────────
# Provider implementations
# ─────────────────────────────────────────────────────────────────────────────

def _gemini_complete(prompt: str, api_key: str) -> Optional[str]:
    """
    Call Gemini generateContent endpoint.
    Returns the text response or None on failure.
    """
    url     = f"{GEMINI_URL}?key={api_key}"
    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "maxOutputTokens": MAX_OUTPUT_TOKENS,
            "temperature": 0.2,   # low temp for code — deterministic outputs
        },
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    for attempt in range(MAX_RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return (
                    data["candidates"][0]["content"]["parts"][0]["text"]
                )
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            if e.code == 429:
                if "quota" in body.lower() and "exceeded" in body.lower():
                    # Hard quota exhausted — no point retrying
                    print(f"[AI/Gemini] Quota exceeded (not a rate limit).")
                    print(f"[AI/Gemini] Fix: use an AI Studio key from aistudio.google.com")
                    print(f"[AI/Gemini] NOT a Google Cloud console key — those require billing.")
                    return None
                if attempt < MAX_RETRIES:
                    print(f"[AI/Gemini] Rate limited — retrying in {RETRY_DELAY}s...")
                    time.sleep(RETRY_DELAY)
                    continue
            print(f"[AI/Gemini] HTTP {e.code}: {body[:200]}")
            return None
        except Exception as e:
            print(f"[AI/Gemini] Error: {e}")
            return None

    return None


def _groq_complete(prompt: str, api_key: str) -> Optional[str]:
    """
    Call Groq chat completions endpoint (OpenAI-compatible).
    Returns the text response or None on failure.
    """
    payload = json.dumps({
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": MAX_OUTPUT_TOKENS,
        "temperature": 0.2,
    }).encode("utf-8")

    req = urllib.request.Request(
        GROQ_URL,
        data=payload,
        headers={
            "Content-Type":  "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    for attempt in range(MAX_RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            if e.code == 429 and attempt < MAX_RETRIES:
                print(f"[AI/Groq] Rate limited — retrying in {RETRY_DELAY}s...")
                time.sleep(RETRY_DELAY)
                continue
            print(f"[AI/Groq] HTTP {e.code}: {body[:200]}")
            return None
        except Exception as e:
            print(f"[AI/Groq] Error: {e}")
            return None

    return None


# ─────────────────────────────────────────────────────────────────────────────
# Public client
# ─────────────────────────────────────────────────────────────────────────────

class AIClient:
    """
    Stateless LLM client. Tries Gemini first, falls back to Groq.

    Instantiate once and reuse across calls:
        client = AIClient()
        response = client.complete(prompt)

    Returns None if no provider is available or all calls fail.
    The caller is responsible for handling None gracefully.
    """

    def __init__(self):
        self._gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
        self._groq_key   = os.environ.get("GROQ_API_KEY", "").strip()

        if self._gemini_key:
            self._provider = "gemini"
        elif self._groq_key:
            self._provider = "groq"
        else:
            self._provider = None

        if self._provider:
            print(f"[AIClient] Provider: {self._provider.upper()}")
        else:
            print("[AIClient] No API key found. AI-assist will be skipped.")
            print("[AIClient] For a FREE key:")
            print("[AIClient]   Gemini: https://aistudio.google.com/app/apikey  (set GEMINI_API_KEY)")
            print("[AIClient]   Groq:   https://console.groq.com/keys           (set GROQ_API_KEY)")

    @property
    def available(self) -> bool:
        """True if at least one provider has a key configured."""
        return self._provider is not None

    def complete(self, prompt: str) -> Optional[str]:
        """
        Send a prompt and return the response text.

        Tries Gemini first. If Gemini fails or is unavailable, tries Groq.
        Returns None if both fail or no key is set.

        Parameters
        ----------
        prompt : str
            The full prompt to send. Keep under ~3000 tokens for free tiers.

        Returns
        -------
        str | None
            Model response text, or None on failure.
        """
        if not self.available:
            return None

        # Try primary provider
        if self._provider == "gemini" and self._gemini_key:
            result = _gemini_complete(prompt, self._gemini_key)
            if result is not None:
                return result
            # Gemini failed — try Groq as fallback
            if self._groq_key:
                print("[AIClient] Gemini failed — falling back to Groq...")
                return _groq_complete(prompt, self._groq_key)

        elif self._provider == "groq" and self._groq_key:
            result = _groq_complete(prompt, self._groq_key)
            if result is not None:
                return result

        return None