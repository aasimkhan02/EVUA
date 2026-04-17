from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

import requests
from bs4 import BeautifulSoup

PHP_DOCS = {
    "8.0": [
        "https://www.php.net/manual/en/migration80.incompatible.php",
        "https://www.php.net/manual/en/migration80.deprecated.php",
        "https://www.php.net/manual/en/migration80.new-features.php",
    ],
    "8.1": [
        "https://www.php.net/manual/en/migration81.incompatible.php",
        "https://www.php.net/manual/en/migration81.deprecated.php",
        "https://www.php.net/manual/en/migration81.new-features.php",
    ],
    "8.2": [
        "https://www.php.net/manual/en/migration82.incompatible.php",
        "https://www.php.net/manual/en/migration82.deprecated.php",
        "https://www.php.net/manual/en/migration82.new-features.php",
    ],
    "8.3": [
        "https://www.php.net/manual/en/migration83.incompatible.php",
        "https://www.php.net/manual/en/migration83.deprecated.php",
        "https://www.php.net/manual/en/migration83.new-features.php",
    ],
}

FUNCTION_RE = re.compile(r"\b([a-z_]+(?:_[a-z0-9]+)+)\(\)", re.IGNORECASE)


@dataclass
class LiveRuleItem:
    category: str
    title: str
    description: str
    php_version: str
    source_url: str


def _cache_key(urls: list[str]) -> str:
    joined = "|".join(sorted(urls))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16]


def fetch_live_rules(php_version: str, cache_dir: str) -> dict:
    urls = PHP_DOCS.get(php_version)
    if not urls:
        raise ValueError(f"Unsupported PHP version for live fetch: {php_version}")

    cache_path = Path(cache_dir)
    cache_path.mkdir(parents=True, exist_ok=True)
    target_file = cache_path / f"rules-{php_version}-{_cache_key(urls)}.json"

    if target_file.exists():
        return json.loads(target_file.read_text(encoding="utf-8"))

    items: list[LiveRuleItem] = []
    deprecated_functions: dict[str, str] = {
        "mysql_*": "mysqli_* or PDO",
        "mysql_query": "mysqli_query($connection, $sql)",
        "mysql_connect": "mysqli_connect($host, $user, $password)",
    }

    for url in urls:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        title = soup.title.string.strip() if soup.title and soup.title.string else url
        text = "\n".join(p.get_text(" ", strip=True) for p in soup.select("li, p"))

        for match in FUNCTION_RE.finditer(text):
            fn = match.group(1)
            if fn.startswith("mysql_") and fn not in deprecated_functions:
                deprecated_functions[fn] = "Use mysqli_* or PDO equivalent"

        for li in soup.select("li"):
            value = li.get_text(" ", strip=True)
            if not value or len(value) < 20:
                continue
            category = "deprecated"
            low = value.lower()
            if "deprecated" in low:
                category = "deprecated"
            elif "removed" in low or "incompatible" in low:
                category = "breaking_change"
            elif "new" in low or "added" in low:
                category = "new_feature"

            items.append(
                LiveRuleItem(
                    category=category,
                    title=title,
                    description=value,
                    php_version=php_version,
                    source_url=url,
                )
            )

    predefined = {
        "deprecated_functions": deprecated_functions,
        "type_system_changes": {
            "weak_to_strict": "Prefer declare(strict_types=1); for migrated code",
            "union_types": "Use union types when docblocks express type unions",
        },
        "namespace_updates": {
            "fully_qualified": "Use explicit use statements for external classes",
        },
        "error_handling": {
            "warnings_to_exceptions": "Audit warnings promoted to TypeError/ValueError in 8.x",
        },
        "syntax_changes": {
            "array_string_access": "Prefer explicit braces and avoid ambiguous offset access",
            "named_arguments": "Named arguments are supported in PHP 8.0+",
            "match_expression": "Consider replacing complex switch blocks with match where safe",
            "nullsafe_operator": "Use ?-> for nullable chained access in PHP 8+",
            "constructor_property_promotion": "Promote constructor properties in PHP 8+ when appropriate",
            "constructor_cleanup": "Remove legacy PHP 4 style constructors",
        },
        "raw_items": [item.__dict__ for item in items],
    }

    target_file.write_text(json.dumps(predefined, indent=2), encoding="utf-8")
    return predefined
