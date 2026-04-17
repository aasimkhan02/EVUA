"""
Rule Engine
Applies applicable migration rules to PHP source code / AST.
"""
import logging
from typing import Optional

from .base_rules import registry
from ..models.migration_models import (
    ASTNode,
    MigrationIssue,
    MigrationResult,
    MigrationStatus,
    PHPVersion,
)

logger = logging.getLogger("evua.rule_engine")


class RuleEngine:
    """
    Runs all registered rules that apply to the given version transition.

    For each match:
    - If ``auto_fixable`` and not ``dry_run``, applies the fix immediately.
    - If ``requires_ai``, records it as an AI-required issue.

    Returns a :class:`MigrationResult` with the (potentially updated) source,
    all matches, all issues, and aggregated stats.
    """

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run

    def run(
        self,
        file_path: str,
        source: str,
        ast: Optional[ASTNode],
        source_version: PHPVersion,
        target_version: PHPVersion,
    ) -> MigrationResult:
        """
        Run all applicable rules against *source* / *ast*.

        Parameters
        ----------
        file_path : str
            Path to the PHP file (used for reporting only).
        source : str
            PHP source code.
        ast : Optional[ASTNode]
            Parsed AST (may be None if parsing failed).
        source_version : PHPVersion
            The PHP version being migrated *from*.
        target_version : PHPVersion
            The PHP version being migrated *to*.

        Returns
        -------
        MigrationResult
        """
        applicable_rules = registry.for_transition(source_version, target_version)
        logger.debug(
            "Running %d rules for %s → %s on %s",
            len(applicable_rules),
            source_version.value,
            target_version.value,
            file_path,
        )

        current_source = source
        all_matches = []
        all_issues: list[MigrationIssue] = []
        auto_fix_count = 0
        ai_required = False

        for rule in applicable_rules:
            try:
                matches = rule.check(
                    current_source, ast, source_version, target_version
                )
            except Exception as exc:
                logger.warning(
                    "Rule %s raised an exception during check: %s",
                    rule.rule_id,
                    exc,
                )
                continue

            for match in matches:
                all_matches.append(match)

                # Build MigrationIssue
                issue = MigrationIssue(
                    rule_id=rule.rule_id,
                    severity=rule.severity,
                    message=rule.description,
                    line=match.start_line,
                    col=match.start_col,
                    original_code=match.matched_text,
                    suggested_fix=match.replacement,
                    auto_fixable=rule.auto_fixable,
                    requires_ai=rule.requires_ai,
                )
                all_issues.append(issue)

                if rule.requires_ai:
                    ai_required = True

                # Apply auto-fixable rules immediately (unless dry run)
                if rule.auto_fixable and not self.dry_run:
                    try:
                        new_source = rule.apply(current_source, match)
                        if new_source != current_source:
                            current_source = new_source
                            auto_fix_count += 1
                            logger.debug(
                                "Auto-fixed rule %s in %s", rule.rule_id, file_path
                            )
                    except Exception as exc:
                        logger.warning(
                            "Rule %s raised an exception during apply: %s",
                            rule.rule_id,
                            exc,
                        )

        # Determine status
        if ai_required:
            status = MigrationStatus.AI_REQUIRED
        elif all_matches:
            status = MigrationStatus.RULE_APPLIED
        else:
            status = MigrationStatus.COMPLETED

        return MigrationResult(
            file_path=file_path,
            original_code=source,
            migrated_code=current_source,
            status=status,
            rule_matches=all_matches,
            issues=all_issues,
            stats={
                "total_matches": len(all_matches),
                "auto_fixable": auto_fix_count,
                "ai_required": sum(1 for i in all_issues if i.requires_ai),
                "rules_applied": len(applicable_rules),
            },
        )
