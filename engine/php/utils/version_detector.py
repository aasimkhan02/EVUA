"""
Version Detector
Heuristically identifies the minimum PHP version required by source code.
"""
import re

from ..models.migration_models import PHPVersion


# Patterns are checked from *newest* to *oldest* so the first match
# returns the highest version the code requires.
_PATTERNS: list[tuple[PHPVersion, str]] = [
    # PHP 8.3
    (PHPVersion.PHP_8_3, r'\bOverride\b'),
    # PHP 8.2
    (PHPVersion.PHP_8_2, r'\breadonly\s+class\b'),
    # PHP 8.1
    (PHPVersion.PHP_8_1, r'\benum\s+\w+'),
    (PHPVersion.PHP_8_1, r'\breadonly\s+(?:public|private|protected)\b'),
    (PHPVersion.PHP_8_1, r'\bfibers?\b'),
    # PHP 8.0
    (PHPVersion.PHP_8_0, r'\bmatch\s*\('),
    (PHPVersion.PHP_8_0, r'#\[\s*[\w\\]+'),      # attributes
    (PHPVersion.PHP_8_0, r'\?\?='),              # null coalescing assignment
    (PHPVersion.PHP_8_0, r'\bthrow\s+new\b.*?;'),  # throw as expression (weak heuristic)
    # PHP 7.4
    (PHPVersion.PHP_7_4, r'\bfn\s*\('),          # arrow functions
    (PHPVersion.PHP_7_4, r'(?<!\?):\s*(?:int|float|string|bool|array|void|object|self)\s*\{'),
    # PHP 7.0
    (PHPVersion.PHP_7_0, r'<=>\s*'),             # spaceship operator
    (PHPVersion.PHP_7_0, r'\byield\s+from\b'),
    (PHPVersion.PHP_7_0, r'\?\s*(?:int|float|string|bool|array|object)\b'),  # nullable hints in 7.1
    # PHP 5.6 indicators (legacy code)
    (PHPVersion.PHP_5_6, r'\bmysql_\w+\s*\('),
    (PHPVersion.PHP_5_6, r'\beregi?\s*\('),
    (PHPVersion.PHP_5_6, r'\bsplit\s*\('),
    (PHPVersion.PHP_5_6, r'\bget_magic_quotes_gpc\s*\('),
    (PHPVersion.PHP_5_6, r'\bcreate_function\s*\('),
]


def detect_version(source: str) -> PHPVersion:
    """
    Heuristically detect the minimum PHP version the source code requires.

    Checks from the newest known version down to PHP 5.6.  Returns the
    version corresponding to the first matched indicator.  Falls back to
    :attr:`PHPVersion.PHP_7_0` when no version-specific syntax is found.

    Parameters
    ----------
    source : str
        PHP source code.

    Returns
    -------
    PHPVersion
    """
    for version, pattern in _PATTERNS:
        if re.search(pattern, source, re.MULTILINE | re.DOTALL):
            return version

    # Default: modern code with no distinctive markers
    return PHPVersion.PHP_7_0
