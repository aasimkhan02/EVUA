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


def load_config(config_path: str | None = None) -> EVUAConfig:
    path = Path(config_path or ".evua.yml")
    if not path.exists():
        return EVUAConfig()

    loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    loaded = _expand_env(loaded)
    return EVUAConfig.model_validate(loaded)
