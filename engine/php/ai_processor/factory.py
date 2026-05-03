from __future__ import annotations

from ..config import EVUAConfig
from .gemini_processor import GeminiProcessor, MockAIProcessor
from .handoff import GeminiHandoffProcessor, OllamaHandoffProcessor
from .ollama_processor import OllamaProcessor


def get_ai_provider(config: EVUAConfig) -> str:
    if config.ollama.api_base:
        return "ollama"
    if config.gemini.api_key:
        return "gemini"
    return "mock"


def build_code_processor(config: EVUAConfig):
    provider = get_ai_provider(config)
    if provider == "ollama":
        return OllamaProcessor(
            api_base=config.ollama.api_base or "http://localhost:11434",
            model=config.ollama.model,
            timeout=config.ollama.timeout,
        )
    if provider == "gemini":
        return GeminiProcessor(
            api_key=config.gemini.api_key or "",
            model=config.gemini.model,
        )
    return MockAIProcessor()


def build_handoff_processor(config: EVUAConfig):
    provider = get_ai_provider(config)
    if provider == "ollama":
        return OllamaHandoffProcessor(
            api_base=config.ollama.api_base or "http://localhost:11434",
            model=config.ollama.model,
            cache_dir=".evua/ai_cache",
            mock_mode=False,
            cache_responses=config.ollama.cache_responses,
            timeout=config.ollama.timeout,
        )
    if provider == "gemini":
        return GeminiHandoffProcessor(
            api_key=config.gemini.api_key,
            model=config.gemini.model,
            cache_dir=".evua/ai_cache",
            mock_mode=config.gemini.mock_mode,
            cache_responses=config.gemini.cache_responses,
        )
    return GeminiHandoffProcessor(
        api_key=None,
        model=config.gemini.model,
        cache_dir=".evua/ai_cache",
        mock_mode=True,
        cache_responses=False,
    )