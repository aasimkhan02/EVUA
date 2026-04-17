from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class PHPVersion(str, Enum):
    PHP_5_6 = "5.6"
    PHP_7_0 = "7.0"
    PHP_7_4 = "7.4"
    PHP_8_0 = "8.0"
    PHP_8_1 = "8.1"
    PHP_8_2 = "8.2"
    PHP_8_3 = "8.3"


class IssueSeverity(str, Enum):
    CRITICAL = "critical"      # Breaks execution
    HIGH = "high"              # Likely to break
    MEDIUM = "medium"          # Deprecated usage
    LOW = "low"                # Style/best-practice
    INFO = "info"              # Informational


class MigrationStatus(str, Enum):
    PENDING = "pending"
    RULE_APPLIED = "rule_applied"
    AI_REQUIRED = "ai_required"
    AI_APPLIED = "ai_applied"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ASTNode:
    node_type: str
    start_line: int
    end_line: int
    start_col: int
    end_col: int
    raw_value: str
    children: list["ASTNode"] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class MigrationIssue:
    rule_id: str
    severity: IssueSeverity
    message: str
    line: int
    col: int
    original_code: str
    suggested_fix: Optional[str] = None
    auto_fixable: bool = False
    requires_ai: bool = False
    context: dict = field(default_factory=dict)


@dataclass
class RuleMatch:
    rule_id: str
    rule_name: str
    matched_text: str
    start_line: int
    end_line: int
    start_col: int
    end_col: int
    replacement: Optional[str] = None
    confidence: float = 1.0
    metadata: dict = field(default_factory=dict)


@dataclass
class FileContext:
    file_path: str
    original_source: str
    source_version: PHPVersion
    target_version: PHPVersion
    encoding: str = "utf-8"
    metadata: dict = field(default_factory=dict)


@dataclass
class MigrationResult:
    file_path: str
    original_code: str
    migrated_code: str
    status: MigrationStatus
    rule_matches: list[RuleMatch] = field(default_factory=list)
    issues: list[MigrationIssue] = field(default_factory=list)
    ai_changes: list[dict] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    stats: dict = field(default_factory=dict)


@dataclass
class PipelineResult:
    job_id: str
    source_version: PHPVersion
    target_version: PHPVersion
    total_files: int
    completed: int = 0
    failed: int = 0
    skipped: int = 0
    results: list[MigrationResult] = field(default_factory=list)
    summary: dict = field(default_factory=dict)