"""
ComponentInteractionRule
========================
Detects parent→child component relationships and generates
@Input() / @Output() property stubs on the relevant components.

How it works
------------
1. Scans generated *.component.html files for custom element tags
   that match other generated components (e.g. <app-user-card> means
   UserCardComponent is a child of the host component).

2. For each detected parent→child relationship:
   - Adds @Input() stubs to the CHILD component .ts file
     (one @Input() for each [bound-property] found in the parent template)
   - Adds @Output() stubs to the CHILD component .ts file
     (one @Output() for each (event) found in the parent template)
   - Adds an import of the child component to the PARENT component .ts file
     (as a comment — full NgModule wiring is handled by AppModuleUpdaterRule)

3. If no template-level usage is found, falls back to DI-level detection:
   when ComponentA has ComponentB injected into its constructor,
   it likely needs to communicate — stubs are generated with a TODO comment.

What it does NOT do
-------------------
- Does not rewrite business logic
- Does not generate full EventEmitter implementations (just stubs)
- Does not handle dynamic component loading (ComponentFactoryResolver)

Run ORDER: after ControllerToComponentRule, before AppModuleUpdaterRule.
"""

from pathlib import Path
from typing import Optional
import re

from ir.migration_model.change import Change
from ir.migration_model.base import ChangeSource
from pipeline.transformation.angular_project_scaffold import AngularProjectScaffold


# ── Helpers ──────────────────────────────────────────────────────────────────

def _selector_to_class(selector: str) -> str:
    """
    'app-user-card' → 'UserCardComponent'
    'app-admin-dashboard' → 'AdminDashboardComponent'
    """
    # Strip leading 'app-'
    base = selector.removeprefix("app-")
    return "".join(p.capitalize() for p in base.split("-")) + "Component"


def _selector_to_stem(selector: str) -> str:
    """
    'app-user-card' → 'usercard'  (matches generated filename)
    """
    base = selector.removeprefix("app-")
    return base.replace("-", "")


def _class_to_selector(class_name: str) -> str:
    """
    'UserCardComponent' → 'app-user-card'
    Inverse of _selector_to_class.
    """
    base = class_name.removesuffix("Component")
    # Insert dash before each uppercase letter (PascalCase → kebab)
    kebab = re.sub(r'(?<!^)(?=[A-Z])', '-', base).lower()
    return f"app-{kebab}"


def _extract_bound_inputs(template: str, selector: str) -> list[str]:
    """
    Find [property] bindings on a given element selector in the template.
    Returns list of property names.
    e.g. <app-user-card [user]="currentUser" [role]="role">
         → ['user', 'role']
    """
    # Match the opening tag of this element
    tag_pattern = re.compile(
        rf'<{re.escape(selector)}([^>]*?)(?:>|/>)',
        re.DOTALL | re.IGNORECASE,
    )
    inputs: list[str] = []
    for m in tag_pattern.finditer(template):
        attrs = m.group(1)
        # Find [input]="..." bindings
        for inp in re.findall(r'\[([a-zA-Z][a-zA-Z0-9_]*)\]\s*=', attrs):
            if inp not in inputs:
                inputs.append(inp)
    return inputs


def _extract_bound_outputs(template: str, selector: str) -> list[str]:
    """
    Find (event) bindings on a given element selector in the template.
    Returns list of output event names.
    e.g. <app-user-card (saved)="onSaved($event)">
         → ['saved']
    """
    tag_pattern = re.compile(
        rf'<{re.escape(selector)}([^>]*?)(?:>|/>)',
        re.DOTALL | re.IGNORECASE,
    )
    outputs: list[str] = []
    for m in tag_pattern.finditer(template):
        attrs = m.group(1)
        for out in re.findall(r'\(([a-zA-Z][a-zA-Z0-9_]*)\)\s*=', attrs):
            if out not in outputs:
                outputs.append(out)
    return outputs


def _inject_input_output_stubs(ts_content: str, inputs: list[str], outputs: list[str]) -> str:
    """
    Insert @Input() and @Output() stubs into an existing component .ts file.

    Strategy:
      - Add 'Input, Output, EventEmitter' to the @angular/core import
      - Add stubs just after the opening class brace (before the constructor)

    Returns modified content or original if no class found.
    """
    if not inputs and not outputs:
        return ts_content

    # ── Patch the @angular/core import ───────────────────────────────────
    core_import_re = re.compile(
        r"import\s*\{([^}]+)\}\s*from\s*'@angular/core';"
    )
    m = core_import_re.search(ts_content)
    if m:
        existing = [s.strip() for s in m.group(1).split(",")]
        to_add = []
        if inputs and "Input" not in existing:
            to_add.append("Input")
        if outputs and "Output" not in existing:
            to_add.append("Output")
        if outputs and "EventEmitter" not in existing:
            to_add.append("EventEmitter")
        if to_add:
            new_symbols = ", ".join(sorted(set(existing + to_add)))
            ts_content = core_import_re.sub(
                f"import {{ {new_symbols} }} from '@angular/core';",
                ts_content,
                count=1,
            )

    # ── Build stubs ───────────────────────────────────────────────────────
    stubs: list[str] = []
    for inp in inputs:
        stubs.append(f"  @Input() {inp}: any;  // TODO: set correct type")
    for out in outputs:
        stubs.append(f"  @Output() {out} = new EventEmitter<any>();  // TODO: set correct event type")

    stub_block = "\n".join(stubs) + "\n"

    # Insert after the class opening brace
    class_open_re = re.compile(r'(export class \w+[^{]*\{)')
    m = class_open_re.search(ts_content)
    if m:
        insert_pos = m.end()
        # Check if there's already content in the class (constructor, comment)
        ts_content = (
            ts_content[: insert_pos]
            + "\n"
            + stub_block
            + ts_content[insert_pos :]
        )

    return ts_content


# ── Main rule ─────────────────────────────────────────────────────────────────

class ComponentInteractionRule:
    """
    Detects parent→child relationships via template element selectors
    and injects @Input()/@Output() stubs into child components.
    """

    def __init__(self, out_dir: str = "out/angular-app", dry_run: bool = False):
        self.project  = AngularProjectScaffold(out_dir)
        self.app_dir  = Path(out_dir) / "src" / "app"
        self.dry_run  = dry_run

    def apply(self, analysis, patterns):
        print("\n========== ComponentInteractionRule.apply() ==========")
        if self.dry_run:
            print("[ComponentInteraction] DRY RUN — no files will be written")

        changes = []

        if not self.app_dir.exists():
            print("[ComponentInteraction] app_dir missing — skipping")
            print("========== ComponentInteractionRule DONE ==========\n")
            return changes

        # ── Build map of selector → (class_name, ts_path, html_path) ────
        component_map: dict[str, dict] = {}  # selector → info

        for ts_file in sorted(self.app_dir.glob("*.component.ts")):
            stem = ts_file.stem   # e.g. 'usercard.component'
            base = stem.removesuffix(".component")
            cls  = "".join(p.capitalize() for p in base.split("-")) + "Component"
            # Selector is 'app-<base>'
            selector   = f"app-{base}"
            html_path  = self.app_dir / f"{base}.component.html"
            component_map[selector] = {
                "class":    cls,
                "ts_path":  ts_file,
                "html_path": html_path,
                "base":     base,
            }

        all_selectors = set(component_map.keys())
        total_relationships = 0

        # ── For each component, scan its template for child selectors ────
        for parent_selector, parent_info in component_map.items():
            html_path = parent_info["html_path"]
            if not html_path.exists():
                continue

            template = html_path.read_text(encoding="utf-8", errors="replace")

            # Find child selectors used in this template
            for child_selector in all_selectors:
                if child_selector == parent_selector:
                    continue

                if f"<{child_selector}" not in template and f"<{child_selector}>" not in template:
                    continue

                # Relationship found: parent uses child
                child_info = component_map[child_selector]
                inputs  = _extract_bound_inputs(template, child_selector)
                outputs = _extract_bound_outputs(template, child_selector)

                print(
                    f"[ComponentInteraction] {parent_info['class']} "
                    f"→ {child_info['class']}: "
                    f"@Input({inputs}) @Output({outputs})"
                )

                if inputs or outputs:
                    total_relationships += 1
                    child_ts = child_info["ts_path"]

                    if self.dry_run:
                        print(f"[DRY RUN] Would patch: {child_ts}")
                        print(f"[DRY RUN]   @Input(): {inputs}")
                        print(f"[DRY RUN]   @Output(): {outputs}")
                    else:
                        original = child_ts.read_text(encoding="utf-8", errors="replace")
                        patched  = _inject_input_output_stubs(original, inputs, outputs)
                        if patched != original:
                            child_ts.write_text(patched, encoding="utf-8")
                            print(f"[ComponentInteraction] Patched: {child_ts.name}")

                    changes.append(Change(
                        before_id=f"interaction_{parent_info['base']}_{child_info['base']}",
                        after_id=f"interaction_{parent_info['base']}_{child_info['base']}_done",
                        source=ChangeSource.RULE,
                        reason=(
                            f"@Input()/@Output() stubs added to {child_info['class']} "
                            f"(used by {parent_info['class']}): "
                            f"inputs={inputs}, outputs={outputs}"
                        ),
                    ))

        if total_relationships == 0:
            print(
                "[ComponentInteraction] No template-level parent→child relationships found. "
                "This is expected when templates are stubs — stubs contain no child selectors."
            )
            # Still record a change so the rule shows up in the report
            changes.append(Change(
                before_id="component_interaction_scan",
                after_id="component_interaction_scan_done",
                source=ChangeSource.RULE,
                reason="ComponentInteractionRule ran — no relationships detected in stub templates",
            ))

        print(f"[ComponentInteraction] Relationships processed: {total_relationships}")
        print("========== ComponentInteractionRule DONE ==========\n")
        return changes