#!/usr/bin/env python3
"""
evua — PHP Migration Rule Generator
====================================
Fetches official PHP migration guidelines from php.net (and the community
cheatsheet mirror), extracts every backward-incompatible change and
deprecated feature, then writes fully-formed Python rule classes into
engine/rule_engine/generated_rules.py that the evua engine can load
automatically.

Usage
-----
    python generate_rules.py                        # fetch + generate
    python generate_rules.py --dry-run              # print rules, don't write
    python generate_rules.py --versions 7.0 8.0     # only specific transitions
    python generate_rules.py --output path/to/out.py

Dependencies: requests, beautifulsoup4, markdownify (optional)
    pip install requests beautifulsoup4

Architecture
------------
  1. MigrationPageFetcher  – HTTP fetches + HTML → structured section text
  2. RuleExtractor          – Heuristic + pattern analysis of section text
                              → list[RawRule]
  3. RuleClassGenerator     – Converts RawRule → Python source code
  4. OutputWriter           – Writes the final .py file
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import sys
import textwrap
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from html.parser import HTMLParser


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("evua.rule_generator")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PHP_NET_BASE = "https://www.php.net/manual/en"

# All migration guide transitions we want to cover
MIGRATION_TRANSITIONS: list[tuple[str, str, str]] = [
    # (from_ver, to_ver, slug)
    ("5.3", "5.4", "migration54"),
    ("5.4", "5.5", "migration55"),
    ("5.5", "5.6", "migration56"),
    ("5.6", "7.0", "migration70"),
    ("7.0", "7.1", "migration71"),
    ("7.1", "7.2", "migration72"),
    ("7.2", "7.3", "migration73"),
    ("7.3", "7.4", "migration74"),
    ("7.4", "8.0", "migration80"),
    ("8.0", "8.1", "migration81"),
    ("8.1", "8.2", "migration82"),
    ("8.2", "8.3", "migration83"),
    ("8.3", "8.4", "migration84"),
    ("8.4", "8.5", "migration85"),
]

# Sub-pages to fetch per migration guide
SECTION_SUFFIXES = [
    ".incompatible",
    ".deprecated",
]

# Severity mapping keywords → severity level
SEVERITY_KEYWORDS: dict[str, str] = {
    "removed":     "CRITICAL",
    "fatal":       "CRITICAL",
    "error":       "CRITICAL",
    "exception":   "HIGH",
    "no longer":   "HIGH",
    "must":        "HIGH",
    "deprecated":  "MEDIUM",
    "discouraged": "MEDIUM",
    "warning":     "MEDIUM",
    "notice":      "LOW",
    "changed":     "LOW",
    "new":         "INFO",
    "added":       "INFO",
}

# Known function-removal mappings  old → replacement
KNOWN_REPLACEMENTS: dict[str, str] = {
    "mysql_connect":          "mysqli_connect",
    "mysql_query":            "mysqli_query",
    "mysql_fetch_array":      "mysqli_fetch_array",
    "mysql_fetch_assoc":      "mysqli_fetch_assoc",
    "mysql_num_rows":         "mysqli_num_rows",
    "mysql_real_escape_string": "mysqli_real_escape_string",
    "mysql_select_db":        "mysqli_select_db",
    "mysql_close":            "mysqli_close",
    "ereg":                   "preg_match",
    "eregi":                  "preg_match",
    "ereg_replace":           "preg_replace",
    "eregi_replace":          "preg_replace",
    "split":                  "preg_split",
    "spliti":                 "preg_split",
    "create_function":        "anonymous function (fn() => ...)",
    "each":                   "foreach or array_key_first()",
    "ldap_sort":              "usort() with ldap_get_entries()",
    "get_magic_quotes_gpc":   "false (magic quotes removed)",
    "get_magic_quotes_runtime": "false (magic quotes removed)",
    "set_magic_quotes_runtime": "no-op (magic quotes removed)",
    "hebrevc":                "Hebrew rtl text handling",
    "convert_cyr_string":     "mb_convert_encoding()",
    "money_format":           "NumberFormatter::formatCurrency()",
    "ezmlm_hash":             "N/A — extension removed",
    "restore_include_path":   "ini_restore('include_path')",
    "__autoload":             "spl_autoload_register()",
    "ReflectionParameter::getClass": "ReflectionParameter::getType()",
    "ReflectionType::__toString":    "ReflectionType::getName()",
    "mb_ereg_replace /e":     "mb_ereg_replace_callback()",
    "preg_replace /e":        "preg_replace_callback()",
    "assert (string)":        "assert (expression/callable)",
    "FILTER_SANITIZE_STRING": "htmlspecialchars() or strip_tags()",
    "FILTER_SANITIZE_STRIPPED": "htmlspecialchars() or strip_tags()",
    "date_sunrise":           "date_sun_info()",
    "date_sunset":            "date_sun_info()",
    "strptime":               "IntlDateFormatter or date_parse_from_format()",
    "gmmktime":               "mktime with UTC adjustment",
    "key() on object":        "get_mangled_object_vars() + key()",
    "current() on object":    "Iterator interface or get_mangled_object_vars()",
    "mhash":                  "hash() with algorithm name",
    "mcrypt_*":               "openssl_* functions",
    "(real) cast":            "(float) cast",
    "(unset) cast":           "= null",
}

# Regex patterns that can detect specific PHP constructs
DETECTION_PATTERNS: dict[str, str] = {
    "mysql_":           r"\bmysql_\w+\s*\(",
    "ereg":             r"\beregi?\s*\(",
    "ereg_replace":     r"\beregi?_replace\s*\(",
    "split":            r"\bsplit\s*\(",
    "spliti":           r"\bspliti\s*\(",
    "create_function":  r"\bcreate_function\s*\(",
    "each":             r"\beach\s*\(",
    "__autoload":       r"\bfunction\s+__autoload\s*\(",
    "mcrypt_":          r"\bmcrypt_\w+\s*\(",
    "money_format":     r"\bmoney_format\s*\(",
    "hebrevc":          r"\bhebrevc\s*\(",
    "convert_cyr_string": r"\bconvert_cyr_string\s*\(",
    "restore_include_path": r"\brestore_include_path\s*\(",
    "get_magic_quotes":  r"\bget_magic_quotes_(gpc|runtime)\s*\(",
    "set_magic_quotes_runtime": r"\bset_magic_quotes_runtime\s*\(",
    "preg_replace_e":   r"""preg_replace\s*\(\s*['"][^'"]*\/e['"]""",
    "mb_ereg_replace_e": r"""mb_ereg_replace\s*\(\s*['"][^'"]*\/e['"]""",
    "real_cast":        r"\(real\)",
    "unset_cast":       r"\(unset\)",
    "call_by_ref":      r"\(\s*&\s*\$\w+",
    "static_call_nonstatic": r"\b\w+::\w+\(",  # rough heuristic
    "curly_offset":     r"\$\w+\{[^}]+\}",
    "FILTER_SANITIZE_STRING": r"\bFILTER_SANITIZE_STRING\b",
    "FILTER_SANITIZE_STRIPPED": r"\bFILTER_SANITIZE_STRIPPED\b",
    "assert_string":    r"\bassert\s*\(\s*['\"]",
    "implicit_nullable": r"function\s+\w+\s*\([^)]*\w+\s+\$\w+\s*=\s*null",
    "optional_before_required": r"function\s+\w+\s*\([^)]*=\s*[^,)]+,[^)]*\$\w+\s*[,)]",
    "dynamic_property": r"\$this->\w+\s*=",
    "date_sunrise":     r"\bdate_sunrise\s*\(",
    "date_sunset":      r"\bdate_sunset\s*\(",
    "strptime":         r"\bstrptime\s*\(",
    "ReflectionType__toString": r"->__toString\(\)",
    "mhash":            r"\bmhash\s*\(",
}


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class MigrationSection:
    """Raw content scraped from one php.net migration sub-page."""
    from_version: str
    to_version: str
    slug: str           # e.g. "migration80"
    section_type: str   # "incompatible" | "deprecated"
    url: str
    title: str
    text: str           # plain text of the section
    items: list[str] = field(default_factory=list)  # individual bullet items


@dataclass
class RawRule:
    """Extracted rule before code generation."""
    rule_id: str
    rule_name: str
    description: str
    severity: str          # CRITICAL / HIGH / MEDIUM / LOW / INFO
    from_version: str
    to_version: str
    section_type: str      # "incompatible" | "deprecated"
    detection_pattern: Optional[str]     # regex or None
    replacement_hint: Optional[str]      # what to replace with
    auto_fixable: bool
    requires_ai: bool
    reference_url: str
    raw_text: str          # original text that generated this rule
    extra_context: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# HTML → text extractor (stdlib only, no bs4 required but supported)
# ---------------------------------------------------------------------------

class _TextExtractor(HTMLParser):
    """Minimal HTML → structured text extractor using stdlib only."""

    def __init__(self):
        super().__init__()
        self._buf: list[str] = []
        self._skip_tags = {"script", "style", "nav", "header", "footer"}
        self._skip_depth = 0
        self._current_tag = ""
        self._in_code = False

    def handle_starttag(self, tag, attrs):
        if tag in self._skip_tags:
            self._skip_depth += 1
        if tag == "code":
            self._in_code = True
            self._buf.append("`")
        if tag in ("li", "p", "h1", "h2", "h3", "h4", "dt"):
            self._buf.append("\n")
        if tag in ("h2", "h3"):
            self._buf.append("## ")
        if tag == "li":
            self._buf.append("• ")

    def handle_endtag(self, tag):
        if tag in self._skip_tags:
            self._skip_depth = max(0, self._skip_depth - 1)
        if tag == "code":
            self._in_code = False
            self._buf.append("`")
        if tag in ("li", "p", "h1", "h2", "h3", "h4", "tr"):
            self._buf.append("\n")

    def handle_data(self, data):
        if self._skip_depth > 0:
            return
        self._buf.append(data)

    def get_text(self) -> str:
        return "".join(self._buf)


def _html_to_text(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html)
    text = parser.get_text()
    # collapse whitespace runs but preserve newlines
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in text.splitlines()]
    # collapse consecutive blank lines
    result = []
    prev_blank = False
    for ln in lines:
        is_blank = ln == ""
        if is_blank and prev_blank:
            continue
        result.append(ln)
        prev_blank = is_blank
    return "\n".join(result)


# ---------------------------------------------------------------------------
# HTTP fetcher with retry + caching
# ---------------------------------------------------------------------------

class MigrationPageFetcher:
    """Fetches PHP migration pages from php.net with local disk caching."""

    CACHE_DIR = Path(".rule_gen_cache")
    USER_AGENT = (
        "Mozilla/5.0 (compatible; evua-rule-generator/1.0; "
        "+https://github.com/evua-project)"
    )
    RETRY_COUNT = 3
    RETRY_DELAY = 2.0   # seconds between retries
    REQUEST_DELAY = 0.8  # be polite to php.net

    def __init__(self, use_cache: bool = True, cache_ttl_hours: int = 168):
        self.use_cache = use_cache
        self.cache_ttl = cache_ttl_hours * 3600
        if use_cache:
            self.CACHE_DIR.mkdir(exist_ok=True)

    def _cache_path(self, url: str) -> Path:
        key = hashlib.md5(url.encode()).hexdigest()
        return self.CACHE_DIR / f"{key}.html"

    def _cache_valid(self, path: Path) -> bool:
        if not path.exists():
            return False
        age = time.time() - path.stat().st_mtime
        return age < self.cache_ttl

    def fetch(self, url: str) -> Optional[str]:
        if self.use_cache:
            cp = self._cache_path(url)
            if self._cache_valid(cp):
                log.debug("Cache hit: %s", url)
                return cp.read_text(encoding="utf-8", errors="replace")

        for attempt in range(1, self.RETRY_COUNT + 1):
            try:
                req = Request(url, headers={"User-Agent": self.USER_AGENT})
                with urlopen(req, timeout=20) as resp:
                    html = resp.read().decode("utf-8", errors="replace")
                if self.use_cache:
                    self._cache_path(url).write_text(html, encoding="utf-8")
                time.sleep(self.REQUEST_DELAY)
                return html
            except HTTPError as exc:
                if exc.code == 404:
                    log.warning("404 — skipping: %s", url)
                    return None
                log.warning("HTTP %d for %s (attempt %d)", exc.code, url, attempt)
            except URLError as exc:
                log.warning("URL error for %s: %s (attempt %d)", url, exc, attempt)
            if attempt < self.RETRY_COUNT:
                time.sleep(self.RETRY_DELAY * attempt)
        return None

    def fetch_section(
        self,
        from_version: str,
        to_version: str,
        slug: str,
        suffix: str,
    ) -> Optional[MigrationSection]:
        url = f"{PHP_NET_BASE}/{slug}{suffix}.php"
        log.info("Fetching %s", url)
        html = self.fetch(url)
        if not html:
            return None

        text = _html_to_text(html)

        # Extract main content area heuristically
        # Find text after "Backward Incompatible Changes" or "Deprecated Features"
        section_type = "incompatible" if "incompatible" in suffix else "deprecated"
        title_marker = (
            "Backward Incompatible Changes"
            if section_type == "incompatible"
            else "Deprecated Features"
        )

        start = text.find(title_marker)
        if start == -1:
            # Try alternative title formats
            alt_markers = [
                "Backward incompatible",
                "Deprecated features",
                "Removed features",
            ]
            for m in alt_markers:
                start = text.lower().find(m.lower())
                if start != -1:
                    break

        content = text[start:] if start != -1 else text

        # Extract bullet items (lines starting with •)
        items = [
            ln.lstrip("• ").strip()
            for ln in content.splitlines()
            if ln.strip().startswith("•") and len(ln.strip()) > 3
        ]

        return MigrationSection(
            from_version=from_version,
            to_version=to_version,
            slug=slug,
            section_type=section_type,
            url=url,
            title=title_marker,
            text=content[:8000],   # cap to avoid huge contexts
            items=items,
        )


# ---------------------------------------------------------------------------
# Rule extractor
# ---------------------------------------------------------------------------

class RuleExtractor:
    """
    Analyses MigrationSection content and produces RawRule objects.
    Uses a layered approach:
      1. Pattern-matching on known function/feature names
      2. Heuristic text analysis for severity + fix hints
      3. Structural analysis of section headings
    """

    # Sections to skip (not actionable code changes)
    SKIP_HEADINGS = {
        "windows support", "other changes", "new features",
        "new classes", "new functions", "new global constants",
        "performance improvements", "ini file handling",
        "ini changes",
    }

    def extract(self, section: MigrationSection) -> list[RawRule]:
        rules: list[RawRule] = []

        # 1. Scan for known patterns in the full text
        for key, pattern in DETECTION_PATTERNS.items():
            if self._pattern_appears_in_source_context(key, section):
                rule = self._build_pattern_rule(key, pattern, section)
                if rule:
                    rules.append(rule)

        # 2. Parse structured sections / headings
        rules.extend(self._parse_headings(section))

        # 3. Parse bullet items
        rules.extend(self._parse_bullets(section))

        # De-duplicate by rule_id
        seen: set[str] = set()
        unique: list[RawRule] = []
        for r in rules:
            if r.rule_id not in seen:
                seen.add(r.rule_id)
                unique.append(r)

        return unique

    def _pattern_appears_in_source_context(
        self, key: str, section: MigrationSection
    ) -> bool:
        """Check if this key's subject is mentioned in the section text."""
        # Normalise key for search
        search = key.replace("_", " ").replace("-", " ").lower()
        search_alt = key.lower().replace("_", "")
        text_lower = section.text.lower()
        return search in text_lower or search_alt in text_lower or key.lower() in text_lower

    def _build_pattern_rule(
        self, key: str, pattern: str, section: MigrationSection
    ) -> Optional[RawRule]:
        replacement = KNOWN_REPLACEMENTS.get(key)
        severity = self._infer_severity(section.text, section.section_type)
        requires_ai = self._requires_ai(key, replacement)
        auto_fixable = bool(replacement) and not requires_ai

        rule_id = self._make_rule_id(section.from_version, section.to_version, key)
        name = self._humanise(key)

        desc = self._build_description(key, replacement, section)

        return RawRule(
            rule_id=rule_id,
            rule_name=name,
            description=desc,
            severity=severity,
            from_version=section.from_version,
            to_version=section.to_version,
            section_type=section.section_type,
            detection_pattern=pattern,
            replacement_hint=replacement,
            auto_fixable=auto_fixable,
            requires_ai=requires_ai,
            reference_url=section.url,
            raw_text=self._find_context(key, section.text),
        )

    def _parse_headings(self, section: MigrationSection) -> list[RawRule]:
        """Extract rules from ## section headings in the text."""
        rules = []
        lines = section.text.splitlines()
        current_heading = ""
        current_body: list[str] = []

        for line in lines:
            if line.startswith("##"):
                if current_heading and current_body:
                    rule = self._heading_to_rule(
                        current_heading,
                        "\n".join(current_body),
                        section,
                    )
                    if rule:
                        rules.append(rule)
                current_heading = line.lstrip("#").strip()
                current_body = []
            else:
                if current_heading:
                    current_body.append(line)

        # last heading
        if current_heading and current_body:
            rule = self._heading_to_rule(
                current_heading,
                "\n".join(current_body),
                section,
            )
            if rule:
                rules.append(rule)

        return rules

    def _heading_to_rule(
        self, heading: str, body: str, section: MigrationSection
    ) -> Optional[RawRule]:
        heading_lower = heading.lower()

        # Skip non-actionable headings
        for skip in self.SKIP_HEADINGS:
            if skip in heading_lower:
                return None

        # Skip very short or generic headings
        if len(heading) < 5 or heading_lower in ("php core", "core", "overview"):
            return None

        severity = self._infer_severity(body, section.section_type)
        key = re.sub(r"[^a-z0-9_]", "_", heading_lower)[:40]
        rule_id = self._make_rule_id(section.from_version, section.to_version, key)

        # Try to find a matching detection pattern
        pattern = None
        replacement = None
        for pk, pv in DETECTION_PATTERNS.items():
            if pk.lower() in heading_lower or heading_lower in pk.lower():
                pattern = pv
                replacement = KNOWN_REPLACEMENTS.get(pk)
                break

        requires_ai = replacement is None or self._requires_ai(key, replacement)
        auto_fixable = bool(replacement) and not requires_ai

        return RawRule(
            rule_id=rule_id,
            rule_name=heading[:80],
            description=self._clean_text(body[:300]),
            severity=severity,
            from_version=section.from_version,
            to_version=section.to_version,
            section_type=section.section_type,
            detection_pattern=pattern,
            replacement_hint=replacement,
            auto_fixable=auto_fixable,
            requires_ai=requires_ai,
            reference_url=section.url,
            raw_text=body[:400],
        )

    def _parse_bullets(self, section: MigrationSection) -> list[RawRule]:
        """Parse bullet point items that aren't covered by heading analysis."""
        rules = []
        for item in section.items:
            if len(item) < 20:
                continue
            # Only create bullet rules for items mentioning specific functions
            func_match = re.search(r"`([a-zA-Z_]\w*)\(\)`", item)
            if not func_match:
                # Try unquoted function names
                func_match = re.search(
                    r"\b([a-zA-Z_]\w+\(\))\b",
                    item
                )
            if not func_match:
                continue

            func_name = func_match.group(1).rstrip("()")
            key = func_name.lower()
            if key in DETECTION_PATTERNS:
                continue  # already covered

            pattern = rf"\b{re.escape(func_name)}\s*\("
            replacement = KNOWN_REPLACEMENTS.get(func_name)
            severity = self._infer_severity(item, section.section_type)

            rule_id = self._make_rule_id(
                section.from_version, section.to_version, key
            )

            rules.append(RawRule(
                rule_id=rule_id,
                rule_name=f"{func_name}() — {section.section_type}",
                description=self._clean_text(item[:300]),
                severity=severity,
                from_version=section.from_version,
                to_version=section.to_version,
                section_type=section.section_type,
                detection_pattern=pattern,
                replacement_hint=replacement,
                auto_fixable=False,
                requires_ai=True,
                reference_url=section.url,
                raw_text=item,
            ))

        return rules

    # ---------------------------------------------------------------- helpers

    @staticmethod
    def _make_rule_id(from_ver: str, to_ver: str, key: str) -> str:
        fv = from_ver.replace(".", "").replace(" ", "")
        tv = to_ver.replace(".", "").replace(" ", "")
        clean_key = re.sub(r"[^A-Z0-9_]", "_", key.upper())[:35].rstrip("_")
        return f"PHP{fv}_{tv}_{clean_key}"

    @staticmethod
    def _humanise(key: str) -> str:
        return key.replace("_", " ").title()

    @staticmethod
    def _infer_severity(text: str, section_type: str) -> str:
        text_lower = text.lower()
        for kw, sev in SEVERITY_KEYWORDS.items():
            if kw in text_lower:
                return sev
        if section_type == "incompatible":
            return "HIGH"
        return "MEDIUM"

    @staticmethod
    def _requires_ai(key: str, replacement: Optional[str]) -> bool:
        """Complex replacements need AI; simple string replacements don't."""
        ai_keys = {
            "mysql_", "create_function", "each", "mcrypt_",
            "preg_replace_e", "mb_ereg_replace_e", "call_by_ref",
            "dynamic_property", "assert_string",
        }
        for ak in ai_keys:
            if ak in key.lower():
                return True
        if replacement and len(replacement) > 60:
            return True
        return False

    @staticmethod
    def _build_description(
        key: str, replacement: Optional[str], section: MigrationSection
    ) -> str:
        base = f"{key.replace('_', ' ')} is"
        if section.section_type == "deprecated":
            base += " deprecated"
        else:
            base += " removed / changed"
        if replacement:
            base += f" in PHP {section.to_version}. Use {replacement} instead."
        else:
            base += f" in PHP {section.to_version}."
        return base

    @staticmethod
    def _find_context(key: str, text: str, window: int = 300) -> str:
        idx = text.lower().find(key.lower().replace("_", " "))
        if idx == -1:
            idx = text.lower().find(key.lower())
        if idx == -1:
            return ""
        start = max(0, idx - 50)
        end = min(len(text), idx + window)
        return text[start:end].strip()

    @staticmethod
    def _clean_text(text: str) -> str:
        text = re.sub(r"`([^`]+)`", r"\1", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()


# ---------------------------------------------------------------------------
# Python code generator
# ---------------------------------------------------------------------------

class RuleClassGenerator:
    """Converts a list of RawRule objects into a Python source file."""

    HEADER = '''"""
Generated PHP Migration Rules
==============================
Auto-generated by evua/generate_rules.py
Source: Official PHP Migration Guides (https://www.php.net/manual/en/)
Generated: {timestamp}

DO NOT EDIT MANUALLY — re-run generate_rules.py to refresh.

This file registers {count} rules covering PHP versions:
  {version_range}
"""
from typing import Optional
import re

from .base_rule import RegexRule, ASTRule, register_rule
from ..models.migration_models import (
    PHPVersion, IssueSeverity, RuleMatch, ASTNode
)

# ---------------------------------------------------------------------------
# Version string → PHPVersion enum helper
# ---------------------------------------------------------------------------

_VER_MAP = {{
    "5.3": PHPVersion.PHP_5_6,   # closest available
    "5.4": PHPVersion.PHP_5_6,
    "5.5": PHPVersion.PHP_5_6,
    "5.6": PHPVersion.PHP_5_6,
    "7.0": PHPVersion.PHP_7_0,
    "7.1": PHPVersion.PHP_7_0,
    "7.2": PHPVersion.PHP_7_0,
    "7.3": PHPVersion.PHP_7_0,
    "7.4": PHPVersion.PHP_7_4,
    "8.0": PHPVersion.PHP_8_0,
    "8.1": PHPVersion.PHP_8_1,
    "8.2": PHPVersion.PHP_8_2,
    "8.3": PHPVersion.PHP_8_3,
    "8.4": PHPVersion.PHP_8_3,   # future-proofing
    "8.5": PHPVersion.PHP_8_3,
}}

'''

    RULE_TEMPLATE = '''
@register_rule
class {class_name}(RegexRule):
    rule_id = {rule_id!r}
    rule_name = {rule_name!r}
    description = (
{description_lines}
    )
    severity = IssueSeverity.{severity}
    auto_fixable = {auto_fixable}
    requires_ai = {requires_ai}
    source_versions = [{source_versions}]
    target_versions = [{target_versions}]
    pattern = {pattern!r}
    replacement = {replacement!r}
    reference_url = {reference_url!r}
{apply_method}
'''

    APPLY_SIMPLE = '''    def apply(self, source: str, match: RuleMatch) -> str:
        return re.sub(self.pattern, {replacement!r}, source, count=1, flags=re.MULTILINE)
'''

    APPLY_AI = '''    def apply(self, source: str, match: RuleMatch) -> str:
        # Complex transformation — delegated to AI processor
        return source
'''

    def generate(self, rules: list[RawRule]) -> str:
        if not rules:
            return '# No rules generated\n'

        # Collect version ranges for header
        versions: set[str] = set()
        for r in rules:
            versions.add(r.from_version)
            versions.add(r.to_version)
        version_range = ", ".join(sorted(versions))

        parts: list[str] = [
            self.HEADER.format(
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M UTC"),
                count=len(rules),
                version_range=version_range,
            )
        ]

        # Group rules by version transition for readability
        by_transition: dict[str, list[RawRule]] = {}
        for rule in rules:
            key = f"{rule.from_version} → {rule.to_version}"
            by_transition.setdefault(key, []).append(rule)

        for transition, t_rules in sorted(by_transition.items()):
            parts.append(f"\n# {'='*70}\n# PHP {transition}\n# {'='*70}\n")
            for rule in t_rules:
                parts.append(self._render_rule(rule))

        return "".join(parts)

    def _render_rule(self, rule: RawRule) -> str:
        class_name = self._to_class_name(rule.rule_id)

        # Escape description for multi-line string
        desc = rule.description.replace('"', '\\"')
        desc_lines = textwrap.wrap(desc, width=72)
        description_lines = "\n".join(
            f'        "{ln}"' for ln in desc_lines
        ) or '        ""'

        source_versions = self._version_list(rule.from_version)
        target_versions = self._version_list(rule.to_version, all_later=True)

        # Pattern — None if no detection pattern
        pattern = rule.detection_pattern or ""
        replacement_str = ""

        # Apply method
        if rule.auto_fixable and rule.replacement_hint:
            apply_method = self.APPLY_SIMPLE.format(
                replacement=rule.replacement_hint
            )
        else:
            apply_method = self.APPLY_AI

        return self.RULE_TEMPLATE.format(
            class_name=class_name,
            rule_id=rule.rule_id,
            rule_name=rule.rule_name[:80],
            description_lines=description_lines,
            severity=rule.severity,
            auto_fixable=rule.auto_fixable,
            requires_ai=rule.requires_ai,
            source_versions=source_versions,
            target_versions=target_versions,
            pattern=pattern,
            replacement=replacement_str,
            reference_url=rule.reference_url,
            apply_method=apply_method,
        )

    @staticmethod
    def _to_class_name(rule_id: str) -> str:
        parts = rule_id.split("_")
        return "".join(p.title() for p in parts) + "Rule"

    @staticmethod
    def _version_list(version: str, all_later: bool = False) -> str:
        """Convert a version string to a comma-separated PHPVersion list."""
        ALL_VERSIONS = [
            "PHP_5_6", "PHP_7_0", "PHP_7_4",
            "PHP_8_0", "PHP_8_1", "PHP_8_2", "PHP_8_3",
        ]
        version_to_enum = {
            "5.3": "PHP_5_6", "5.4": "PHP_5_6", "5.5": "PHP_5_6",
            "5.6": "PHP_5_6", "7.0": "PHP_7_0", "7.1": "PHP_7_0",
            "7.2": "PHP_7_0", "7.3": "PHP_7_0", "7.4": "PHP_7_4",
            "8.0": "PHP_8_0", "8.1": "PHP_8_1", "8.2": "PHP_8_2",
            "8.3": "PHP_8_3", "8.4": "PHP_8_3", "8.5": "PHP_8_3",
        }
        enum_name = version_to_enum.get(version, "PHP_5_6")
        if all_later:
            idx = ALL_VERSIONS.index(enum_name) if enum_name in ALL_VERSIONS else 0
            later = ALL_VERSIONS[idx:]
            return ", ".join(f"PHPVersion.{v}" for v in later)
        return f"PHPVersion.{enum_name}"


# ---------------------------------------------------------------------------
# Output writer
# ---------------------------------------------------------------------------

class OutputWriter:
    def write(self, code: str, output_path: str):
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(code, encoding="utf-8")
        log.info("Written %d lines to %s", len(code.splitlines()), path)

    def print(self, code: str):
        print(code)


# ---------------------------------------------------------------------------
# Rule manifest (JSON summary)
# ---------------------------------------------------------------------------

class ManifestWriter:
    """Writes a machine-readable JSON manifest alongside the rule file."""

    def write(self, rules: list[RawRule], output_path: str):
        manifest_path = Path(output_path).with_suffix(".json")
        data = {
            "generated": datetime.now().isoformat(),
            "total_rules": len(rules),
            "source": "https://www.php.net/manual/en/",
            "rules": [
                {
                    "id": r.rule_id,
                    "name": r.rule_name,
                    "severity": r.severity,
                    "from": r.from_version,
                    "to": r.to_version,
                    "section": r.section_type,
                    "auto_fixable": r.auto_fixable,
                    "requires_ai": r.requires_ai,
                    "pattern": r.detection_pattern,
                    "replacement": r.replacement_hint,
                    "reference": r.reference_url,
                    "description": r.description,
                }
                for r in rules
            ],
        }
        manifest_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        log.info("Manifest written to %s", manifest_path)


# ---------------------------------------------------------------------------
# Progress reporter
# ---------------------------------------------------------------------------

class ProgressReporter:
    def __init__(self, total: int):
        self.total = total
        self.done = 0

    def tick(self, label: str):
        self.done += 1
        pct = int(self.done / self.total * 100)
        bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
        print(f"\r  [{bar}] {pct:3d}%  {label[:50]:<50}", end="", flush=True)

    def done_msg(self):
        print()  # newline after bar


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

class RuleGenerator:
    """
    Top-level orchestrator:
      fetch → extract → generate → write
    """

    def __init__(
        self,
        versions: Optional[list[str]] = None,
        use_cache: bool = True,
        dry_run: bool = False,
        output_path: str = "engine/rule_engine/generated_rules.py",
        write_manifest: bool = True,
    ):
        self.versions = versions
        self.fetcher = MigrationPageFetcher(use_cache=use_cache)
        self.extractor = RuleExtractor()
        self.generator = RuleClassGenerator()
        self.writer = OutputWriter()
        self.manifest = ManifestWriter()
        self.dry_run = dry_run
        self.output_path = output_path
        self.write_manifest = write_manifest

    def run(self) -> list[RawRule]:
        transitions = self._filter_transitions()
        total_fetches = len(transitions) * len(SECTION_SUFFIXES)
        progress = ProgressReporter(total_fetches)

        print(f"\n{'═'*60}")
        print(f"  evua PHP Rule Generator")
        print(f"  Covering {len(transitions)} version transitions")
        print(f"{'═'*60}\n")

        all_rules: list[RawRule] = []
        sections_fetched = 0

        for from_ver, to_ver, slug in transitions:
            for suffix in SECTION_SUFFIXES:
                label = f"PHP {from_ver}→{to_ver} {suffix.lstrip('.')}"
                progress.tick(label)

                section = self.fetcher.fetch_section(
                    from_ver, to_ver, slug, suffix
                )
                if section is None:
                    continue

                sections_fetched += 1
                rules = self.extractor.extract(section)
                all_rules.extend(rules)
                log.debug(
                    "  %s → %d rules extracted", label, len(rules)
                )

        progress.done_msg()

        # Deduplicate globally by rule_id
        seen: set[str] = set()
        unique_rules: list[RawRule] = []
        for r in all_rules:
            if r.rule_id not in seen:
                seen.add(r.rule_id)
                unique_rules.append(r)

        print(f"\n  ✓ Fetched {sections_fetched} sections")
        print(f"  ✓ Extracted {len(unique_rules)} unique rules")

        # Generate code
        code = self.generator.generate(unique_rules)

        if self.dry_run:
            print(f"\n{'─'*60}")
            print("  DRY RUN — output preview (first 120 lines):\n")
            for i, line in enumerate(code.splitlines()[:120]):
                print(f"  {line}")
            print(f"{'─'*60}\n")
        else:
            self.writer.write(code, self.output_path)
            if self.write_manifest:
                self.manifest.write(unique_rules, self.output_path)
            print(f"\n  ✓ Written to {self.output_path}")

        # Print summary table
        self._print_summary(unique_rules)

        return unique_rules

    def _filter_transitions(self) -> list[tuple[str, str, str]]:
        if not self.versions:
            return MIGRATION_TRANSITIONS
        filtered = []
        for fv, tv, slug in MIGRATION_TRANSITIONS:
            if fv in self.versions or tv in self.versions:
                filtered.append((fv, tv, slug))
        return filtered

    @staticmethod
    def _print_summary(rules: list[RawRule]):
        by_severity: dict[str, int] = {}
        by_transition: dict[str, int] = {}
        auto_count = sum(1 for r in rules if r.auto_fixable)
        ai_count = sum(1 for r in rules if r.requires_ai)

        for r in rules:
            by_severity[r.severity] = by_severity.get(r.severity, 0) + 1
            key = f"{r.from_version} → {r.to_version}"
            by_transition[key] = by_transition.get(key, 0) + 1

        print(f"\n{'═'*60}")
        print("  Rule Summary")
        print(f"{'═'*60}")
        print(f"  {'Total rules:':<30} {len(rules)}")
        print(f"  {'Auto-fixable:':<30} {auto_count}")
        print(f"  {'Requires AI:':<30} {ai_count}")
        print()
        print("  Severity breakdown:")
        for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]:
            n = by_severity.get(sev, 0)
            bar = "█" * min(n, 40)
            print(f"    {sev:<10} {n:>4}  {bar}")
        print()
        print("  Rules per transition:")
        for trans in sorted(by_transition):
            print(f"    PHP {trans:<15}  {by_transition[trans]:>4} rules")
        print(f"{'═'*60}\n")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate evua PHP migration rules from official php.net guides",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
        Examples:
          # Generate all rules (default)
          python generate_rules.py

          # Only generate rules for specific version transitions
          python generate_rules.py --versions 7.4 8.0

          # Preview without writing
          python generate_rules.py --dry-run

          # Custom output path
          python generate_rules.py --output my_project/rules/generated.py

          # Force re-fetch (ignore cache)
          python generate_rules.py --no-cache
        """),
    )
    parser.add_argument(
        "--versions", nargs="+", metavar="VER",
        help="PHP versions to include (e.g. 7.4 8.0 8.1)",
    )
    parser.add_argument(
        "--output", default="engine/rule_engine/generated_rules.py",
        metavar="PATH",
        help="Output file path (default: engine/rule_engine/generated_rules.py)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print generated code without writing to disk",
    )
    parser.add_argument(
        "--no-cache", action="store_true",
        help="Bypass HTTP cache (re-fetch from php.net)",
    )
    parser.add_argument(
        "--no-manifest", action="store_true",
        help="Skip writing the JSON manifest file",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Enable verbose (DEBUG) logging",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    generator = RuleGenerator(
        versions=args.versions,
        use_cache=not args.no_cache,
        dry_run=args.dry_run,
        output_path=args.output,
        write_manifest=not args.no_manifest,
    )

    try:
        rules = generator.run()
        sys.exit(0 if rules else 1)
    except KeyboardInterrupt:
        print("\n\nInterrupted.")
        sys.exit(130)
    except Exception as exc:
        log.error("Fatal error: %s", exc, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
