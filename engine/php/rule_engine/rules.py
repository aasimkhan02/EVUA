"""
Built-in PHP Migration Rules
Covers PHP 5.x → 7.x → 8.x transitions.
"""
import re
from typing import Optional

from .base_rule import RegexRule, ASTRule, register_rule
from ..models.migration_models import (
    PHPVersion, IssueSeverity, RuleMatch, ASTNode
)
from ..ast_parser.visitor import find_nodes, find_nodes_matching


# =============================================================================
# PHP 5.x → 7.0
# =============================================================================

@register_rule
class MySQLExtRule(RegexRule):
    rule_id = "PHP56_MYSQL_EXT"
    rule_name = "Deprecated mysql_* extension"
    description = (
        "The mysql_* functions are removed in PHP 7. "
        "Replace with mysqli_* or PDO."
    )
    severity = IssueSeverity.CRITICAL
    auto_fixable = False
    requires_ai = True
    source_versions = [PHPVersion.PHP_5_6]
    target_versions = [PHPVersion.PHP_7_0, PHPVersion.PHP_7_4,
                       PHPVersion.PHP_8_0, PHPVersion.PHP_8_1,
                       PHPVersion.PHP_8_2, PHPVersion.PHP_8_3]
    pattern = r"\bmysql_\w+\s*\("
    replacement = ""
    reference_url = "https://www.php.net/manual/en/migration70.incompatible.php"

    def apply(self, source: str, match: RuleMatch) -> str:
        # Cannot auto-fix: hand off to AI
        return source


@register_rule
class EregFunctionRule(RegexRule):
    rule_id = "PHP56_EREG_FUNCTIONS"
    rule_name = "Removed ereg_* functions"
    description = "ereg/eregi/ereg_replace removed in PHP 7. Use preg_* equivalents."
    severity = IssueSeverity.CRITICAL
    auto_fixable = True
    source_versions = [PHPVersion.PHP_5_6]
    target_versions = [PHPVersion.PHP_7_0, PHPVersion.PHP_7_4,
                       PHPVersion.PHP_8_0, PHPVersion.PHP_8_1]
    pattern = r"\beregi?(_replace)?\s*\("
    replacement = ""

    _MAPPINGS = {
        "ereg(": "preg_match(",
        "eregi(": "preg_match(",
        "ereg_replace(": "preg_replace(",
        "eregi_replace(": "preg_replace(",
    }

    def apply(self, source: str, match: RuleMatch) -> str:
        for old, new in self._MAPPINGS.items():
            if match.matched_text.lower().startswith(old.lower()):
                return source.replace(match.matched_text, new, 1)
        return source


@register_rule
class SplitFunctionRule(RegexRule):
    rule_id = "PHP56_SPLIT_FUNCTION"
    rule_name = "Removed split() function"
    description = "split() removed in PHP 7. Use preg_split() or explode()."
    severity = IssueSeverity.CRITICAL
    auto_fixable = True
    source_versions = [PHPVersion.PHP_5_6]
    pattern = r"\bsplit\s*\("
    replacement = "preg_split("

    def apply(self, source: str, match: RuleMatch) -> str:
        return source.replace(match.matched_text, "preg_split(", 1)


@register_rule
class PassByReferenceCallRule(RegexRule):
    rule_id = "PHP56_CALL_TIME_PASS_BY_REF"
    rule_name = "Call-time pass-by-reference removed"
    description = "Passing by reference at call-time (func(&$var)) is removed in PHP 7."
    severity = IssueSeverity.HIGH
    auto_fixable = False
    requires_ai = True
    source_versions = [PHPVersion.PHP_5_6]
    pattern = r"\(\s*&\s*\$\w+"
    replacement = ""


@register_rule
class PregReplaceEModifierRule(RegexRule):
    rule_id = "PHP56_PREG_E_MODIFIER"
    rule_name = "preg_replace /e modifier removed"
    description = "The /e modifier in preg_replace is removed. Use preg_replace_callback()."
    severity = IssueSeverity.CRITICAL
    auto_fixable = False
    requires_ai = True
    source_versions = [PHPVersion.PHP_5_6]
    pattern = r"""preg_replace\s*\(\s*['"][^'"]*\/e['"]"""
    replacement = ""


@register_rule
class SetMagicQuotesRule(RegexRule):
    rule_id = "PHP56_MAGIC_QUOTES"
    rule_name = "magic_quotes_* removed"
    description = "get_magic_quotes_gpc/runtime removed in PHP 7."
    severity = IssueSeverity.HIGH
    auto_fixable = True
    source_versions = [PHPVersion.PHP_5_6]
    pattern = r"\bget_magic_quotes_(gpc|runtime)\s*\(\s*\)"
    replacement = "false"

    def apply(self, source: str, match: RuleMatch) -> str:
        compiled = re.compile(self.pattern, re.MULTILINE)
        return compiled.sub("false", source, count=1)


# =============================================================================
# PHP 7.x → 8.0
# =============================================================================

@register_rule
class CreateFunctionRule(RegexRule):
    rule_id = "PHP7X_CREATE_FUNCTION"
    rule_name = "create_function() removed"
    description = "create_function() is removed in PHP 8. Use anonymous functions."
    severity = IssueSeverity.CRITICAL
    auto_fixable = False
    requires_ai = True
    source_versions = [PHPVersion.PHP_7_0, PHPVersion.PHP_7_4]
    target_versions = [PHPVersion.PHP_8_0, PHPVersion.PHP_8_1,
                       PHPVersion.PHP_8_2, PHPVersion.PHP_8_3]
    pattern = r"\bcreate_function\s*\("
    replacement = ""


@register_rule
class EachFunctionRule(RegexRule):
    rule_id = "PHP7X_EACH_FUNCTION"
    rule_name = "each() removed"
    description = "each() is removed in PHP 8. Use foreach or list()/array_key_first()."
    severity = IssueSeverity.CRITICAL
    auto_fixable = False
    requires_ai = True
    source_versions = [PHPVersion.PHP_7_0, PHPVersion.PHP_7_4]
    target_versions = [PHPVersion.PHP_8_0, PHPVersion.PHP_8_1,
                       PHPVersion.PHP_8_2, PHPVersion.PHP_8_3]
    pattern = r"\beach\s*\("
    replacement = ""


@register_rule
class ReflectionParameterClassRule(RegexRule):
    rule_id = "PHP7X_REFLECTION_CLASS"
    rule_name = "ReflectionParameter::getClass() removed"
    description = "Use ReflectionParameter::getType() in PHP 8."
    severity = IssueSeverity.HIGH
    auto_fixable = True
    source_versions = [PHPVersion.PHP_7_0, PHPVersion.PHP_7_4]
    pattern = r"->getClass\(\)"
    replacement = "->getType()"

    def apply(self, source: str, match: RuleMatch) -> str:
        return source.replace(match.matched_text, "->getType()", 1)


@register_rule
class ImplicitFloatToIntRule(RegexRule):
    rule_id = "PHP8X_IMPLICIT_FLOAT_INT"
    rule_name = "Implicit float to int conversion"
    description = (
        "PHP 8 deprecates implicit non-lossless float-to-int coercions. "
        "Use explicit (int) cast."
    )
    severity = IssueSeverity.MEDIUM
    auto_fixable = False
    requires_ai = True
    source_versions = [PHPVersion.PHP_7_0, PHPVersion.PHP_7_4]
    target_versions = [PHPVersion.PHP_8_0, PHPVersion.PHP_8_1,
                       PHPVersion.PHP_8_2, PHPVersion.PHP_8_3]
    # Pattern: assignment of a float expression to int-typed param/property
    pattern = r"\$\w+\s*=\s*[\d.]+\s*[*/]\s*[\d.]+"
    replacement = ""


@register_rule
class NullableTypeSyntaxRule(RegexRule):
    """PHP 7.1+ nullable type hint ?Type — no-op rule for < 7.1 awareness."""
    rule_id = "PHP71_NULLABLE_TYPE"
    rule_name = "Nullable type hints (?Type)"
    description = "Nullable types introduced in PHP 7.1 — not available in 5.x/7.0."
    severity = IssueSeverity.INFO
    auto_fixable = False
    source_versions = [PHPVersion.PHP_5_6, PHPVersion.PHP_7_0]
    pattern = r"\?\s*(?:int|float|string|bool|array|object|callable|iterable|self|parent)\b"
    replacement = ""


# =============================================================================
# PHP 8.0 → 8.1/8.2/8.3
# =============================================================================

@register_rule
class DynamicPropertyRule(ASTRule):
    rule_id = "PHP82_DYNAMIC_PROPERTIES"
    rule_name = "Deprecated dynamic properties"
    description = (
        "Dynamic (undeclared) properties are deprecated in PHP 8.2 "
        "and will be removed in PHP 9. Declare them or use #[AllowDynamicProperties]."
    )
    severity = IssueSeverity.HIGH
    auto_fixable = False
    requires_ai = True
    source_versions = [PHPVersion.PHP_8_0, PHPVersion.PHP_8_1]
    target_versions = [PHPVersion.PHP_8_2, PHPVersion.PHP_8_3]
    pattern = r"\$this->\w+\s*="
    reference_url = "https://www.php.net/manual/en/migration82.deprecated.php"

    def check(
        self,
        source: str,
        ast: Optional[ASTNode],
        source_version: PHPVersion,
        target_version: PHPVersion,
    ) -> list[RuleMatch]:
        if ast is None:
            return []

        matches: list[RuleMatch] = []

        # Collect all declared properties in the class
        class_nodes = find_nodes(ast, "class_declaration")
        for cls in class_nodes:
            declared = set()
            assignments: list[ASTNode] = []

            for node in find_nodes(cls, "property_declaration"):
                raw = node.raw_value
                var_m = re.search(r"\$(\w+)", raw)
                if var_m:
                    declared.add(var_m.group(1))

            for node in find_nodes(cls, "expression_statement"):
                if "$this->" in node.raw_value:
                    m = re.match(r"\$this->(\w+)\s*=", node.raw_value.strip())
                    if m and m.group(1) not in declared:
                        matches.append(RuleMatch(
                            rule_id=self.rule_id,
                            rule_name=self.rule_name,
                            matched_text=node.raw_value,
                            start_line=node.start_line,
                            end_line=node.end_line,
                            start_col=node.start_col,
                            end_col=node.end_col,
                            replacement=None,
                            metadata={"property": m.group(1), "class": cls.metadata.get("name")},
                        ))
        return matches

    def apply(self, source: str, match: RuleMatch) -> str:
        return source  # requires AI


@register_rule
class ReadonlyPropertyRule(ASTRule):
    rule_id = "PHP81_READONLY"
    rule_name = "Readonly properties (PHP 8.1)"
    description = "Consider using readonly properties for immutable values."
    severity = IssueSeverity.INFO
    auto_fixable = False
    requires_ai = False
    source_versions = [PHPVersion.PHP_8_0]
    target_versions = [PHPVersion.PHP_8_1, PHPVersion.PHP_8_2, PHPVersion.PHP_8_3]
    pattern = r""
    reference_url = "https://www.php.net/manual/en/migration81.new-features.php"

    def check(
        self,
        source: str,
        ast: Optional[ASTNode],
        source_version: PHPVersion,
        target_version: PHPVersion,
    ) -> list[RuleMatch]:
        # Informational only – surfaces properties that could be readonly
        return []

    def apply(self, source: str, match: RuleMatch) -> str:
        return source


@register_rule
class StringableInterfaceRule(ASTRule):
    rule_id = "PHP80_STRINGABLE"
    rule_name = "Stringable interface auto-implementation"
    description = (
        "Classes with __toString now implicitly implement Stringable in PHP 8. "
        "Consider adding it explicitly for clarity."
    )
    severity = IssueSeverity.INFO
    auto_fixable = False
    requires_ai = False
    source_versions = [PHPVersion.PHP_7_0, PHPVersion.PHP_7_4]
    target_versions = [PHPVersion.PHP_8_0, PHPVersion.PHP_8_1,
                       PHPVersion.PHP_8_2, PHPVersion.PHP_8_3]
    pattern = r""

    def check(
        self,
        source: str,
        ast: Optional[ASTNode],
        source_version: PHPVersion,
        target_version: PHPVersion,
    ) -> list[RuleMatch]:
        matches = []
        for cls in find_nodes(ast or ASTNode("", 0, 0, 0, 0, ""), "class_declaration"):
            has_to_string = any(
                n.metadata.get("name") == "__toString"
                for n in find_nodes(cls, "function_declaration")
            )
            implements = cls.metadata.get("implements", [])
            if has_to_string and "Stringable" not in implements:
                matches.append(RuleMatch(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    matched_text=cls.raw_value,
                    start_line=cls.start_line,
                    end_line=cls.start_line,
                    start_col=cls.start_col,
                    end_col=cls.end_col,
                    metadata={"class": cls.metadata.get("name")},
                ))
        return matches

    def apply(self, source: str, match: RuleMatch) -> str:
        return source


@register_rule
class DeprecatedFunctionRule(RegexRule):
    rule_id = "PHP80_DEPRECATED_FUNCS"
    rule_name = "PHP 8.0 deprecated functions"
    description = "Functions deprecated or removed in PHP 8.0."
    severity = IssueSeverity.HIGH
    auto_fixable = True
    source_versions = [PHPVersion.PHP_7_0, PHPVersion.PHP_7_4]
    target_versions = [PHPVersion.PHP_8_0, PHPVersion.PHP_8_1,
                       PHPVersion.PHP_8_2, PHPVersion.PHP_8_3]
    # cover a selection of deprecated functions
    pattern = (
        r"\b(implode|array_key_exists|stripos|strpos|substr_count|"
        r"number_format|str_pad|str_repeat)\s*\(\s*NULL"
    )
    replacement = ""

    def apply(self, source: str, match: RuleMatch) -> str:
        # Replace NULL first argument with appropriate default
        return source


@register_rule
class TypedPropertyRule(ASTRule):
    rule_id = "PHP74_TYPED_PROPERTIES"
    rule_name = "Typed properties (PHP 7.4)"
    description = "Add type declarations to class properties for PHP 7.4+."
    severity = IssueSeverity.INFO
    auto_fixable = False
    requires_ai = True
    source_versions = [PHPVersion.PHP_5_6, PHPVersion.PHP_7_0]
    target_versions = [PHPVersion.PHP_7_4, PHPVersion.PHP_8_0,
                       PHPVersion.PHP_8_1, PHPVersion.PHP_8_2]
    pattern = r""

    def check(
        self,
        source: str,
        ast: Optional[ASTNode],
        source_version: PHPVersion,
        target_version: PHPVersion,
    ) -> list[RuleMatch]:
        if ast is None:
            return []
        matches = []
        for node in find_nodes(ast, "property_declaration"):
            raw = node.raw_value.strip()
            # If no type hint found
            has_type = bool(re.match(
                r"(?:public|private|protected|static|readonly)?\s+"
                r"(?:int|float|string|bool|array|object|mixed|\?\w+)\s+\$",
                raw
            ))
            if not has_type and "$" in raw:
                matches.append(RuleMatch(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    matched_text=raw,
                    start_line=node.start_line,
                    end_line=node.end_line,
                    start_col=node.start_col,
                    end_col=node.end_col,
                    metadata={"raw": raw},
                ))
        return matches

    def apply(self, source: str, match: RuleMatch) -> str:
        return source  # AI required


@register_rule
class UnionTypeRule(ASTRule):
    rule_id = "PHP80_UNION_TYPES"
    rule_name = "Union types (PHP 8.0)"
    description = (
        "PHP 8.0 introduces union types (int|string). "
        "Older code using docblock types can be upgraded."
    )
    severity = IssueSeverity.INFO
    auto_fixable = False
    requires_ai = True
    source_versions = [PHPVersion.PHP_7_0, PHPVersion.PHP_7_4]
    target_versions = [PHPVersion.PHP_8_0, PHPVersion.PHP_8_1,
                       PHPVersion.PHP_8_2, PHPVersion.PHP_8_3]
    pattern = r"@param\s+(\w+\|\w+)"

    def check(
        self,
        source: str,
        ast: Optional[ASTNode],
        source_version: PHPVersion,
        target_version: PHPVersion,
    ) -> list[RuleMatch]:
        matches = []
        pat = re.compile(r"@param\s+(\w+\|\w+)\s+(\$\w+)", re.MULTILINE)
        for m in pat.finditer(source):
            line = source[: m.start()].count("\n") + 1
            matches.append(RuleMatch(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                matched_text=m.group(),
                start_line=line,
                end_line=line,
                start_col=0,
                end_col=len(m.group()),
                metadata={"union_type": m.group(1), "param": m.group(2)},
            ))
        return matches

    def apply(self, source: str, match: RuleMatch) -> str:
        return source  # AI decides where/how to apply


@register_rule
class NamedArgumentsRule(RegexRule):
    rule_id = "PHP80_NAMED_ARGS"
    rule_name = "Named arguments opportunity (PHP 8.0)"
    description = (
        "PHP 8.0 supports named arguments. "
        "Complex calls with many bool args are candidates."
    )
    severity = IssueSeverity.INFO
    auto_fixable = False
    requires_ai = True
    source_versions = [PHPVersion.PHP_7_0, PHPVersion.PHP_7_4]
    target_versions = [PHPVersion.PHP_8_0, PHPVersion.PHP_8_1,
                       PHPVersion.PHP_8_2, PHPVersion.PHP_8_3]
    # Heuristic: function calls with 4+ arguments
    pattern = r"\b\w+\s*\([^)]{80,}\)"
    replacement = ""

    def apply(self, source: str, match: RuleMatch) -> str:
        return source
