from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class GeminiConfig(BaseModel):
    api_key: str | None = None
    model: str = "gemini-1.5-pro"
    max_tokens: int = 2000
    cache_responses: bool = True
    mock_mode: bool = False


class OllamaConfig(BaseModel):
    api_base: str | None = None
    model: str = "gemma3:latest"
    timeout: int = 120
    temperature: float = 0.1
    cache_responses: bool = True


class RulesConfig(BaseModel):
    source: str = "local"
    cache_dir: str = ".evua/rules_cache"


class MigrationConfig(BaseModel):
    dry_run: bool = False
    parallel_jobs: int = 4
    max_file_size_mb: int = 10


class ReportConfig(BaseModel):
    format: str = "json"
    include_unchanged_files: bool = False
    ai_confidence_threshold: float = 0.7


class EVUAConfig(BaseModel):
    gemini: GeminiConfig = Field(default_factory=GeminiConfig)
    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    rules: RulesConfig = Field(default_factory=RulesConfig)
    migration: MigrationConfig = Field(default_factory=MigrationConfig)
    report: ReportConfig = Field(default_factory=ReportConfig)


def _expand_env(value: Any) -> Any:
    if isinstance(value, str):
        pattern = re.compile(r"\$\{([^}]+)\}")

        def repl(match: re.Match[str]) -> str:
            key = match.group(1)
            return os.getenv(key, "")

        return pattern.sub(repl, value)
    if isinstance(value, dict):
        return {k: _expand_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand_env(v) for v in value]
    return value


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _load_dotenv_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def load_config(config_path: str | None = None) -> EVUAConfig:
    for candidate in (Path(".env"), Path("backend/.env"), Path("engine/php/.env")):
        _load_dotenv_file(candidate)

    env_config = EVUAConfig(
        gemini=GeminiConfig(
            api_key=os.getenv("GEMINI_API_KEY") or None,
            model=os.getenv("GEMINI_MODEL") or "gemini-1.5-pro",
            max_tokens=_env_int("GEMINI_MAX_TOKENS", 2000),
            cache_responses=_env_bool("GEMINI_CACHE_RESPONSES", True),
            mock_mode=_env_bool("GEMINI_MOCK_MODE", False),
        ),
        ollama=OllamaConfig(
            api_base=os.getenv("OLLAMA_API_BASE") or None,
            model=os.getenv("OLLAMA_MODEL") or "gemma3:latest",
            timeout=_env_int("OLLAMA_TIMEOUT", 120),
            temperature=_env_float("OLLAMA_TEMPERATURE", 0.1),
            cache_responses=_env_bool("OLLAMA_CACHE_RESPONSES", True),
        ),
    )

    path = Path(config_path or ".evua.yml")
    if not path.exists():
        return env_config

    loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    loaded = _expand_env(loaded)
    yaml_config = EVUAConfig.model_validate(loaded)

    return EVUAConfig(
        gemini=GeminiConfig(
            api_key=env_config.gemini.api_key or yaml_config.gemini.api_key,
            model=env_config.gemini.model if os.getenv("GEMINI_MODEL") else yaml_config.gemini.model,
            max_tokens=env_config.gemini.max_tokens if os.getenv("GEMINI_MAX_TOKENS") else yaml_config.gemini.max_tokens,
            cache_responses=env_config.gemini.cache_responses if os.getenv("GEMINI_CACHE_RESPONSES") else yaml_config.gemini.cache_responses,
            mock_mode=env_config.gemini.mock_mode if os.getenv("GEMINI_MOCK_MODE") else yaml_config.gemini.mock_mode,
        ),
        ollama=OllamaConfig(
            api_base=env_config.ollama.api_base or yaml_config.ollama.api_base,
            model=env_config.ollama.model if os.getenv("OLLAMA_MODEL") else yaml_config.ollama.model,
            timeout=env_config.ollama.timeout if os.getenv("OLLAMA_TIMEOUT") else yaml_config.ollama.timeout,
            temperature=env_config.ollama.temperature if os.getenv("OLLAMA_TEMPERATURE") else yaml_config.ollama.temperature,
            cache_responses=env_config.ollama.cache_responses if os.getenv("OLLAMA_CACHE_RESPONSES") else yaml_config.ollama.cache_responses,
        ),
        rules=yaml_config.rules,
        migration=yaml_config.migration,
        report=yaml_config.report,
    )
