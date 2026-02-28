from pipeline.risk.levels import RiskLevel
from pipeline.patterns.roles import SemanticRole
from pipeline.transformation.angular_project_scaffold import AngularProjectScaffold
from pipeline.transformation.result import TransformationResult
from ir.migration_model.change import Change
from ir.migration_model.base import ChangeSource
from pathlib import Path


class DirectiveRiskRule:
    """
    Assesses risk for AngularJS directives and emits Changes for each one.

    All directives are MANUAL — there is no deterministic 1-to-1 migration
    from AngularJS directives to Angular. A directive may become:
      - An Angular @Component (element directive)
      - An Angular @Directive (attribute/class directive)
      - A combination of both with complex lifecycle hook rewrites

    This rule also emits Change objects so directives appear in:
      - manual_required list in the report
      - generated_files (a stub .directive-stub.ts per directive)

    It runs ALONGSIDE the risk rules (assess() interface), but also
    writes stub files so the harness sees the directive was acknowledged.
    """

    def __init__(self, out_dir="out/angular-app"):
        self.app_dir = Path(out_dir) / "src" / "app"

    def assess(self, analysis, patterns, transformation):
        risk_by_change   = {}
        reason_by_change = {}

        directives = getattr(analysis, "directives", []) or []

        if not directives:
            return risk_by_change, reason_by_change

        self.app_dir.mkdir(parents=True, exist_ok=True)

        for d in directives:
            name          = getattr(d, "name", "unknown")
            has_compile   = getattr(d, "has_compile", False)
            has_link      = getattr(d, "has_link", False)
            transclude    = getattr(d, "transclude", False)

            # Build a human-readable reason
            signals = []
            if has_compile:
                signals.append("$compile")
            if has_link:
                signals.append("link()")
            if transclude:
                signals.append("transclude")

            signal_str = f" [{', '.join(signals)}]" if signals else ""
            reason = (
                f"AngularJS directive{signal_str} — no deterministic Angular migration. "
                f"Manually convert to @Component or @Directive."
            )

            # Write a stub file acknowledging the directive
            stub_name = f"{name.lower()}.directive-stub.ts"
            stub_path = self.app_dir / stub_name

            if not stub_path.exists():
                stub_content = (
                    f"// TODO: Migrate AngularJS directive '{name}' to Angular\n"
                    f"//\n"
                    f"// This directive used: {', '.join(signals) if signals else 'none detected'}\n"
                    f"//\n"
                    f"// Migration options:\n"
                    f"//   - Element directive  → @Component with selector: '{name.lower()}'\n"
                    f"//   - Attribute directive → @Directive with selector: '[{name.lower()}]'\n"
                    f"//\n"
                    f"// Reference: https://angular.io/guide/attribute-directives\n\n"
                    f"import {{ Directive, ElementRef }} from '@angular/core';\n\n"
                    f"// STUB — replace with actual migration\n"
                    f"@Directive({{ selector: '[{name.lower()}]' }})\n"
                    f"export class {name[0].upper()}{name[1:]}Directive {{\n"
                    f"  constructor(private el: ElementRef) {{\n"
                    f"    // TODO: port link() / compile() logic here\n"
                    f"  }}\n"
                    f"}}\n"
                )
                stub_path.write_text(stub_content, encoding="utf-8")

            # Emit a synthetic Change so cli.py captures this directive
            # before_id uses the directive's id so _resolve_name returns the name
            change_id = f"directive_{d.id}"
            change = Change(
                before_id=d.id,
                after_id=change_id,
                source=ChangeSource.RULE,
                reason=f"AngularJS directive '{name}' requires manual migration written to {stub_path}",
            )

            # Register in transformation so cli.py sees it
            if hasattr(transformation, "changes"):
                transformation.changes.append(change)

            risk_by_change[change.id]   = RiskLevel.MANUAL
            reason_by_change[change.id] = reason

        return risk_by_change, reason_by_change