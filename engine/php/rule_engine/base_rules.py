"""
Rule Engine Base
Defines the Rule ABC and the global RuleRegistry.
"""
import re
from abc import ABC, abstractmethod
from typing import Optional
from ..models.migration_models import (
    RuleMatch, MigrationIssue, ASTNode, PHPVersion, IssueSeverity
)


class Rule(ABC):
    """
    Abstract base for all migration rules.
    Each rule targets a specific PHP version transition.
    """

    #: Unique rule identifier, e.g. "PHP56_MYSQL_EXT"
    rule_id: str = ""
    #: Human-readable name
    rule_name: str = ""
    #: Short description
    description: str = ""
    #: Severity if not fixed
    severity: IssueSeverity = IssueSeverity.MEDIUM
    #: Can this rule auto-apply a fix?
    auto_fixable: bool = False
    #: Does this rule need AI for the fix?
    requires_ai: bool = False
    #: Applicable source versions
    source_versions: list[PHPVersion] = []
    #: Applicable target versions
    target_versions: list[PHPVersion] = []
    #: Reference URL (e.g. PHP migration guide)
    reference_url: str = ""

    @abstractmethod
    def check(
        self,
        source: str,
        ast: Optional[ASTNode],
        source_version: PHPVersion,
        target_version: PHPVersion,
    ) -> list[RuleMatch]:
        """
        Analyse source/AST and return all matches found.
        """
        ...

    @abstractmethod
    def apply(self, source: str, match: RuleMatch) -> str:
        """
        Apply the rule's fix to source and return the modified source.
        Only called when auto_fixable is True.
        """
        ...

    def is_applicable(
        self, source_version: PHPVersion, target_version: PHPVersion
    ) -> bool:
        src_ok = not self.source_versions or source_version in self.source_versions
        tgt_ok = not self.target_versions or target_version in self.target_versions
        return src_ok and tgt_ok


class RegexRule(Rule):
    """
    Convenience base for rules that only need a regex pattern.
    """

    #: The regex pattern to search for
    pattern: str = ""
    #: The replacement string (supports backreferences)
    replacement: str = ""
    #: Flags for re.compile
    flags: int = re.MULTILINE

    def check(
        self,
        source: str,
        ast: Optional[ASTNode],
        source_version: PHPVersion,
        target_version: PHPVersion,
    ) -> list[RuleMatch]:
        matches = []
        compiled = re.compile(self.pattern, self.flags)
        for m in compiled.finditer(source):
            line_no = source[: m.start()].count("\n") + 1
            col = m.start() - source[: m.start()].rfind("\n") - 1
            replacement = m.expand(self.replacement) if self.replacement else self.replacement
            matches.append(
                RuleMatch(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    matched_text=m.group(),
                    start_line=line_no,
                    end_line=line_no,
                    start_col=col,
                    end_col=col + len(m.group()),
                    replacement=replacement,
                    metadata={"groups": m.groups(), "named": m.groupdict()},
                )
            )
        return matches

    def apply(self, source: str, match: RuleMatch) -> str:
        if match.replacement is None or self.replacement == "":
            return source
        compiled = re.compile(self.pattern, self.flags)
        return compiled.sub(self.replacement, source, count=1)


class ASTRule(Rule):
    """
    Base for rules that operate on the AST.
    Default apply() does a simple text substitution.
    """

    def apply(self, source: str, match: RuleMatch) -> str:
        if match.replacement is None:
            return source
        return source.replace(match.matched_text, match.replacement, 1)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class RuleRegistry:
    """Singleton registry of all available rules."""

    _instance: Optional["RuleRegistry"] = None
    _rules: dict[str, Rule] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._rules = {}
        return cls._instance

    def register(self, rule: Rule):
        self._rules[rule.rule_id] = rule

    def get(self, rule_id: str) -> Optional[Rule]:
        return self._rules.get(rule_id)

    def all(self) -> list[Rule]:
        return list(self._rules.values())

    def for_transition(
        self, source_version: PHPVersion, target_version: PHPVersion
    ) -> list[Rule]:
        return [
            r for r in self._rules.values()
            if r.is_applicable(source_version, target_version)
        ]


# Global registry instance
registry = RuleRegistry()


def register_rule(rule_class):
    """Class decorator to auto-register a rule."""
    instance = rule_class()
    registry.register(instance)
    return rule_class