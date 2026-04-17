from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .php_parser import PHPASTParser


@dataclass
class CodeMetrics:
    lines_of_code: int
    cyclomatic_complexity: int
    nesting_depth: int
    dependencies: int
    test_coverage_estimate: float


@dataclass
class AnalysisFinding:
    category: str
    line: int
    snippet: str
    reason: str
    confidence: float


def _max_nesting_depth(source: str) -> int:
    depth = 0
    best = 0
    for char in source:
        if char == "{":
            depth += 1
            best = max(best, depth)
        elif char == "}":
            depth = max(0, depth - 1)
    return best


def _cyclomatic_complexity(source: str) -> int:
    patterns = [r"\bif\b", r"\belseif\b", r"\bfor\b", r"\bforeach\b", r"\bwhile\b", r"\bcase\b", r"\bcatch\b", r"\?", r"&&", r"\|\|"]
    return 1 + sum(len(re.findall(p, source)) for p in patterns)


def _test_coverage_estimate(file_path: str) -> float:
    path = Path(file_path)
    name = path.stem.lower()
    project_root = path.parents[2] if len(path.parents) >= 3 else path.parent
    tests = list(project_root.rglob("*test*.php")) + list(project_root.rglob("*Test*.php"))
    if not tests:
        return 0.0
    direct = any(name in t.stem.lower() for t in tests)
    if direct:
        return 0.8
    return min(0.6, len(tests) / 30.0)


def analyze_php_source(file_path: str, source: str) -> tuple[object | None, list[AnalysisFinding], CodeMetrics]:
    ast = None
    try:
        ast = PHPASTParser(source).parse()
    except Exception:
        ast = None

    findings: list[AnalysisFinding] = []
    patterns = [
        ("deprecated_function", r"\bmysql_\w+\s*\(", "mysql_* was removed and needs migration", 0.95),
        ("dynamic_code", r"\beval\s*\(", "eval() is hard to migrate safely and should be reviewed", 0.99),
        ("variable_function", r"\$\w+\s*\(", "variable function call may require AI review", 0.78),
        ("magic_method", r"__\w+", "magic methods can hide behavior changes across versions", 0.7),
        ("error_suppression", r"@\s*[a-zA-Z_]\w*\s*\(", "error suppression operator can mask migration issues", 0.86),
        ("global_access", r"\bglobal\s+\$", "global state may increase migration risk", 0.65),
        ("array_string_access", r"\$\w+\{[^}]+\}", "string/array offset braces are risky in modern PHP", 0.82),
    ]

    lines = source.splitlines()
    for category, pattern, reason, confidence in patterns:
        for m in re.finditer(pattern, source, flags=re.MULTILINE):
            line_idx = source[: m.start()].count("\n") + 1
            snippet = lines[line_idx - 1].strip() if line_idx - 1 < len(lines) else m.group(0)
            findings.append(
                AnalysisFinding(
                    category=category,
                    line=line_idx,
                    snippet=snippet[:240],
                    reason=reason,
                    confidence=confidence,
                )
            )

    metrics = CodeMetrics(
        lines_of_code=len([line for line in lines if line.strip()]),
        cyclomatic_complexity=_cyclomatic_complexity(source),
        nesting_depth=_max_nesting_depth(source),
        dependencies=len(re.findall(r"\b(?:use|require|require_once|include|include_once)\b", source)),
        test_coverage_estimate=round(_test_coverage_estimate(file_path), 2),
    )

    return ast, findings, metrics
