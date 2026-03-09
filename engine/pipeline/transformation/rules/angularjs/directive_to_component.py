"""
DirectiveToComponentRule
========================

Converts AngularJS .directive() definitions into Angular stubs.

Migration strategy by restrict type
-------------------------------------
'E'  (element)   → @Component  with selector 'app-<name>'
                   Generates:  <name>.component.ts
                               <name>.component.html
'A'  (attribute) → @Directive  with selector '[<name>]'
                   Generates:  <name>.directive.ts
'EA' (both)      → @Component  (element usage is primary)
'C'  (class)     → @Directive  (class selectors are attribute-like)

For each directive the rule reads from analysis.directives (RawDirective)
which now carries:
    .name          str       AngularJS camelCase directive name
    .restrict      str       'E', 'A', 'EA', 'C', etc.  (default 'EA')
    .has_compile   bool
    .has_link      bool
    .transclude    bool
    .scope_bindings dict     {bindingName: '@'/'='/'&'}
    .template      str|None  inline template
    .template_url  str|None  templateUrl

Generated files are plain Angular stubs with:
  - TODO comments explaining what to migrate
  - @Input() declarations for scope bindings
  - Warning comment if compile/link/transclude detected

Pipeline order
--------------
Must run BEFORE AppModuleUpdaterRule so generated *.component.ts /
*.directive.ts files are picked up and added to declarations[].

Change constructor
------------------
Uses Change(before_id, after_id, source=ChangeSource.RULE, reason=...)
matching the pattern used by all other rules.
"""

import re
from pathlib import Path

from ir.migration_model.change import Change
from ir.migration_model.base import ChangeSource
from pipeline.transformation.angular_project_scaffold import AngularProjectScaffold


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _to_pascal(name: str) -> str:
    """'userCard' → 'UserCard',  'loading-spinner' → 'LoadingSpinner'"""
    # Handle camelCase → split on boundaries then capitalise
    name = re.sub(r'([A-Z])', r'-\1', name).lstrip('-')
    parts = re.split(r'[-_]', name)
    return "".join(p.capitalize() for p in parts if p)


def _to_kebab(name: str) -> str:
    """'userCard' → 'user-card',  'loadingSpinner' → 'loading-spinner'"""
    s = re.sub(r'([A-Z])', r'-\1', name).lstrip('-').lower()
    return re.sub(r'[-_]+', '-', s)


def _safe_stem(name: str) -> str:
    """'userCard' → 'usercard'  (for filename stem, no separator)"""
    return re.sub(r'[^a-z0-9]', '', name.lower())


def _binding_type(sigil: str) -> str:
    return {"@": "string", "=": "any", "&": "() => any"}.get(sigil, "any")


# ─────────────────────────────────────────────────────────────────────────────
# Code generators
# ─────────────────────────────────────────────────────────────────────────────

def _generate_component(directive) -> tuple[str, str]:
    """
    Generate Angular @Component TS + HTML for element directives.
    Returns (ts_code, html_code).
    """
    name        = directive.name
    pascal      = _to_pascal(name)
    kebab       = _to_kebab(name)
    class_name  = pascal + "Component"
    selector    = f"app-{kebab}"
    stem        = _safe_stem(name)

    scope       = getattr(directive, "scope_bindings", {}) or {}
    has_compile = getattr(directive, "has_compile", False)
    has_link    = getattr(directive, "has_link", False)
    transclude  = getattr(directive, "transclude", False)
    template    = getattr(directive, "template", None)
    template_url = getattr(directive, "template_url", None)

    # Build @Input() lines from scope bindings
    input_lines = []
    for binding_name, sigil in scope.items():
        ts_type = _binding_type(sigil)
        input_lines.append(f"  @Input() {binding_name}: {ts_type};")

    inputs_block = ("\n" + "\n".join(input_lines) + "\n") if input_lines else ""

    # Complexity warnings
    warnings = []
    if has_compile:
        warnings.append("  // ⚠ Original directive used compile() — DOM manipulation must be rewritten manually.")
    if has_link:
        warnings.append("  // ⚠ Original directive used link() — port DOM logic to ngAfterViewInit().")
    if transclude:
        warnings.append("  // ⚠ Original directive used transclusion — use <ng-content> in template.")
    warnings_block = ("\n" + "\n".join(warnings) + "\n") if warnings else ""

    # Template origin comment
    if template:
        tpl_comment = f"  // Original inline template: {template[:80]!r}{'...' if len(template) > 80 else ''}"
    elif template_url:
        tpl_comment = f"  // Original templateUrl: {template_url}"
    else:
        tpl_comment = "  // TODO: add template content"

    imports = ["Component"]
    if input_lines:
        imports.append("Input")
    imports_str = ", ".join(imports)

    ts_code = (
        f"import {{ {imports_str} }} from '@angular/core';\n"
        f"\n"
        f"@Component({{\n"
        f"  selector: '{selector}',\n"
        f"  templateUrl: './{stem}.component.html'\n"
        f"}})\n"
        f"export class {class_name} {{\n"
        f"{inputs_block}"
        f"{warnings_block}"
        f"{tpl_comment}\n"
        f"\n"
        f"  // TODO: migrate directive logic from AngularJS '{name}'\n"
        f"}}\n"
    )

    # HTML stub
    if template:
        # Migrate the inline template lightly (just include as comment + raw)
        html_code = (
            f"<!-- Angular template for {class_name} — migrated from AngularJS directive '{name}' -->\n"
            f"<!-- TODO: migrate the original AngularJS template below to Angular syntax -->\n"
            f"<!-- Original template:\n"
            f"{template}\n"
            f"-->\n"
            f"<ng-content></ng-content>\n"
        )
    else:
        html_code = (
            f"<!-- Angular template for {class_name} — migrated from AngularJS directive '{name}' -->\n"
            f"<!-- TODO: add template content (original templateUrl: {template_url or 'none'}) -->\n"
            f"<ng-content></ng-content>\n"
        )

    return ts_code, html_code


def _generate_directive(directive) -> str:
    """
    Generate Angular @Directive TS for attribute-only directives.
    Returns ts_code.
    """
    name        = directive.name
    pascal      = _to_pascal(name)
    kebab       = _to_kebab(name)
    class_name  = pascal + "Directive"
    selector    = f"[{kebab}]"

    scope       = getattr(directive, "scope_bindings", {}) or {}
    has_compile = getattr(directive, "has_compile", False)
    has_link    = getattr(directive, "has_link", False)

    input_lines = []
    for binding_name, sigil in scope.items():
        ts_type = _binding_type(sigil)
        input_lines.append(f"  @Input() {binding_name}: {ts_type};")

    inputs_block = ("\n" + "\n".join(input_lines) + "\n") if input_lines else ""

    warnings = []
    if has_compile:
        warnings.append("  // ⚠ Original directive used compile() — rewrite as host listener logic.")
    if has_link:
        warnings.append("  // ⚠ Original directive used link() — port to ngOnInit() / @HostListener.")
    warnings_block = ("\n" + "\n".join(warnings) + "\n") if warnings else ""

    imports = ["Directive", "ElementRef"]
    if input_lines:
        imports.append("Input")
    imports_str = ", ".join(imports)

    return (
        f"import {{ {imports_str} }} from '@angular/core';\n"
        f"\n"
        f"@Directive({{ selector: '{selector}' }})\n"
        f"export class {class_name} {{\n"
        f"{inputs_block}"
        f"{warnings_block}"
        f"  constructor(private el: ElementRef) {{\n"
        f"    // TODO: migrate directive logic from AngularJS '{name}'\n"
        f"  }}\n"
        f"}}\n"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Rule
# ─────────────────────────────────────────────────────────────────────────────

class DirectiveToComponentRule:
    """
    Converts AngularJS directives to Angular @Component or @Directive stubs.

    Reads  : analysis.directives  — list of RawDirective objects
    Writes : src/app/<name>.component.ts + .html   for element directives
             src/app/<name>.directive.ts            for attribute-only
    Effect : AppModuleUpdaterRule (runs after) picks up *.component.ts and
             *.directive.ts files and adds classes to declarations[].
    """

    def __init__(self, out_dir: str = "out/angular-app", dry_run: bool = False):
        self.project = AngularProjectScaffold(out_dir)
        self.app_dir = Path(out_dir) / "src" / "app"
        self.dry_run = dry_run

    def apply(self, analysis, patterns):
        print("\n========== DirectiveToComponentRule.apply() ==========")
        if self.dry_run:
            print("[DirectiveToComponent] DRY RUN — no files will be written")

        changes = []

        if not self.dry_run:
            self.project.ensure()

        directives = getattr(analysis, "directives", []) or []
        print(f"[DirectiveToComponent] Directives detected: {len(directives)}")

        if not directives:
            print("[DirectiveToComponent] No directives — nothing to do.")
            print("========== DirectiveToComponentRule DONE ==========\n")
            return changes

        seen: set[str] = set()

        for d in directives:
            name = getattr(d, "name", None)
            if not name or name in seen:
                continue
            seen.add(name)

            restrict    = getattr(d, "restrict", "EA").upper()
            stem        = _safe_stem(name)
            pascal      = _to_pascal(name)
            is_element  = "E" in restrict
            is_attr_only = restrict == "A" or restrict == "C"

            print(f"[DirectiveToComponent] {name!r}  restrict={restrict!r}  "
                  f"link={getattr(d,'has_link',False)}  "
                  f"compile={getattr(d,'has_compile',False)}")

            if is_element:
                # Element directive (with or without attribute) → @Component
                ts_code, html_code = _generate_component(d)
                ts_path   = self.app_dir / f"{stem}.component.ts"
                html_path = self.app_dir / f"{stem}.component.html"

                if self.dry_run:
                    print(f"[DRY RUN] Would write: {ts_path}")
                else:
                    self.app_dir.mkdir(parents=True, exist_ok=True)
                    if not ts_path.exists():
                        ts_path.write_text(ts_code, encoding="utf-8")
                        print(f"[DirectiveToComponent] Written: {ts_path}")
                    if not html_path.exists():
                        html_path.write_text(html_code, encoding="utf-8")
                        print(f"[DirectiveToComponent] Written: {html_path}")

                changes.append(Change(
                    before_id=f"directive_{name}",
                    after_id=f"component_{stem}",
                    source=ChangeSource.RULE,
                    reason=f"AngularJS directive '{name}' (restrict={restrict}) → Angular @Component stub",
                ))

            else:
                # Attribute-only directive → @Directive
                ts_code = _generate_directive(d)
                ts_path = self.app_dir / f"{stem}.directive.ts"

                if self.dry_run:
                    print(f"[DRY RUN] Would write: {ts_path}")
                else:
                    self.app_dir.mkdir(parents=True, exist_ok=True)
                    if not ts_path.exists():
                        ts_path.write_text(ts_code, encoding="utf-8")
                        print(f"[DirectiveToComponent] Written: {ts_path}")

                changes.append(Change(
                    before_id=f"directive_{name}",
                    after_id=f"directive_{stem}",
                    source=ChangeSource.RULE,
                    reason=f"AngularJS directive '{name}' (restrict={restrict}) → Angular @Directive stub",
                ))

        print(f"[DirectiveToComponent] {len(changes)} directive(s) migrated.")
        print("========== DirectiveToComponentRule DONE ==========\n")
        return changes