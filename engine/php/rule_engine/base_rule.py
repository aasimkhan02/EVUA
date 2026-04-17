"""
base_rule.py — compatibility shim.
All rule base classes live in base_rules.py; this module re-exports them
so that both ``from .base_rule import …`` and ``from .base_rules import …``
work correctly.
"""
from .base_rules import (  # noqa: F401
    Rule,
    RegexRule,
    ASTRule,
    RuleRegistry,
    registry,
    register_rule,
)

__all__ = [
    "Rule",
    "RegexRule",
    "ASTRule",
    "RuleRegistry",
    "registry",
    "register_rule",
]
