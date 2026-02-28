import re
from pathlib import Path
from ir.migration_model.change import Change
from ir.migration_model.base import ChangeSource
from pipeline.transformation.angular_project_scaffold import AngularProjectScaffold
from pipeline.transformation.helpers import iter_controllers
from pipeline.transformation.template_migrator import (
    extract_controller_template,
    migrate_template,
    migrate_template_from_raw,
)


class ControllerToComponentRule:
    def __init__(self, out_dir: str = "out/angular-app", dry_run: bool = False):
        self.project      = AngularProjectScaffold(out_dir)
        self.out_dir      = Path(out_dir) / "src" / "app"
        self.routing_path = self.out_dir / "app-routing.module.ts"
        self.dry_run      = dry_run

    def apply(self, analysis, patterns):
        print("\n========== ControllerToComponentRule.apply() ==========")
        if self.dry_run:
            print("[ControllerToComponent] DRY RUN — no files will be written")

        changes = []

        if not self.dry_run:
            self.project.ensure()

        routing_code     = self.routing_path.read_text(encoding="utf-8") if self.routing_path.exists() else ""
        original_routing = routing_code

        # ── Build template lookup from raw_templates (preserves raw_html) ──
        # analysis.raw_templates = RawTemplate objects from HTMLAnalyzer
        # analysis.templates     = IR Template objects (raw_html already stripped)
        raw_templates = getattr(analysis, "raw_templates", []) or []

        # Map controller_name → raw_html for dedicated per-controller files
        template_html_by_controller: dict[str, str] = {}
        for t in raw_templates:
            ctrl     = getattr(t, "controller", None)
            raw_html = getattr(t, "raw_html", "") or ""
            if ctrl and raw_html.strip():
                template_html_by_controller[ctrl] = raw_html

        # Scan ALL html files for ng-controller references (monolithic index.html pattern)
        # A single file may contain multiple controllers — index each one
        all_html_sources: list[str] = []
        for t in raw_templates:
            raw_html = getattr(t, "raw_html", "") or ""
            if raw_html.strip():
                all_html_sources.append(raw_html)
                # Register any controller found in this file that we don't have yet
                for ctrl_match in re.finditer(r'\bng-controller\s*=\s*["\'](\w+)', raw_html):
                    ctrl_name = ctrl_match.group(1)
                    if ctrl_name not in template_html_by_controller:
                        template_html_by_controller[ctrl_name] = raw_html

        controllers = list(iter_controllers(analysis, patterns))
        print(f"[ControllerToComponent] Controllers detected: {len(controllers)}")
        print(f"[ControllerToComponent] Template sources available: {list(template_html_by_controller.keys())}")

        if not controllers:
            print("[ControllerToComponent]  No controllers matched.")
            changes.append(Change(
                before_id="debug_controller_rule",
                after_id="debug_controller_rule_ran",
                source=ChangeSource.RULE,
                reason="ControllerToComponentRule ran but matched 0 controllers"
            ))
            return changes

        for c in controllers:
            source_html  = template_html_by_controller.get(c.name)
            raw_template = next(
                (t for t in raw_templates if getattr(t, "controller", None) == c.name),
                None
            )
            routing_code = self._emit_component(c, routing_code, changes, source_html, raw_template)

        if not self.dry_run:
            self.routing_path.write_text(routing_code, encoding="utf-8")
            print("[ControllerToComponent] Routing module updated")

        changes.append(Change(
            before_id="routing_module",
            after_id="angular_routing_module",
            source=ChangeSource.RULE,
            reason=f"Angular Router configured written to {self.routing_path}",
        ))

        print("========== ControllerToComponentRule DONE ==========\n")
        return changes

    # -----------------------------------------------------------------------

    def _resolve_html_content(self, c, source_html: str | None, raw_template) -> tuple[str, str]:
        """
        Returns (html_content, method_used).

        Priority:
          1. Extract controller fragment from monolithic HTML (best)
          2. Migrate a full dedicated template file
          3. Build from RawTemplate structured data
          4. Minimal stub
        """
        class_name = c.name.replace("Controller", "").replace("Ctrl", "") + "Component"

        if source_html:
            fragment = extract_controller_template(source_html, c.name)
            if fragment:
                content = (
                    f"<!-- Angular template for {class_name} —"
                    f" migrated from AngularJS {c.name} -->\n"
                    + fragment
                )
                return content, "fragment_extracted"

            # Dedicated template file with no ng-controller wrapper
            other_controllers = re.findall(r'\bng-controller\s*=\s*["\'](\w+)', source_html)
            if not other_controllers or other_controllers == [c.name]:
                content = (
                    f"<!-- Angular template for {class_name} — migrated from AngularJS -->\n"
                    + migrate_template(source_html)
                )
                return content, "full_file_migrated"

        if raw_template:
            content = (
                f"<!-- Angular template for {class_name} (built from detected patterns) -->\n"
                + migrate_template_from_raw(raw_template)
            )
            return content, "raw_template_fallback"

        base = c.name.replace("Controller", "").replace("Ctrl", "").lower()
        content = (
            f"<!-- Angular template for {class_name} -->\n"
            f"<!-- TODO: no AngularJS template found — migrate manually -->\n"
            f"<!-- Common patterns: ng-repeat → *ngFor | ng-if → *ngIf | ng-model → [(ngModel)] -->\n"
            f"<h2>{class_name}</h2>\n"
        )
        return content, "stub"

    def _emit_component(self, c, routing_code: str, changes: list,
                        source_html: str | None, raw_template) -> str:
        base       = c.name.replace("Controller", "").replace("Ctrl", "").lower()
        class_name = c.name.replace("Controller", "").replace("Ctrl", "") + "Component"
        selector   = f"app-{base}"
        ts_path    = self.out_dir / f"{base}.component.ts"
        html_path  = self.out_dir / f"{base}.component.html"

        # ── TypeScript component ──────────────────────────────────────────
        ts_code = (
            f"import {{ Component }} from '@angular/core';\n\n"
            f"@Component({{\n"
            f"  selector: '{selector}',\n"
            f"  templateUrl: './{base}.component.html'\n"
            f"}})\n"
            f"export class {class_name} {{}}\n"
        )

        if self.dry_run:
            print(f"[DRY RUN] Would write: {ts_path}")
        else:
            ts_path.parent.mkdir(parents=True, exist_ok=True)
            if not ts_path.exists() or ts_path.read_text(encoding="utf-8") != ts_code:
                ts_path.write_text(ts_code, encoding="utf-8")
                print(f"[ControllerToComponent] Written: {ts_path}")

        changes.append(Change(
            before_id=c.id,
            after_id=f"component_{c.id}",
            source=ChangeSource.RULE,
            reason=f"Controller -> Angular Component written to {ts_path}",
        ))

        # ── HTML template ─────────────────────────────────────────────────
        html_content, method = self._resolve_html_content(c, source_html, raw_template)
        print(f"[ControllerToComponent] Template for {c.name}: method={method}")

        if self.dry_run:
            print(f"[DRY RUN] Would write: {html_path}")
            print(f"[DRY RUN] Preview:\n{html_content[:300]}")
        else:
            if not html_path.exists():
                html_path.write_text(html_content, encoding="utf-8")
                print(f"[ControllerToComponent] Template written: {html_path}")

        changes.append(Change(
            before_id=f"{c.id}_html",
            after_id=f"component_html_{c.id}",
            source=ChangeSource.RULE,
            reason=f"Component template written to {html_path}",
        ))

        # ── Routing ───────────────────────────────────────────────────────
        import_line = f"import {{ {class_name} }} from './{base}.component';"
        if import_line not in routing_code:
            routing_code = import_line + "\n" + routing_code

        route_entry = f"{{ path: '{base}', component: {class_name} }}"
        if route_entry not in routing_code:
            if "const routes: Routes = [];" in routing_code:
                routing_code = routing_code.replace(
                    "const routes: Routes = [];",
                    f"const routes: Routes = [\n  {route_entry}\n];"
                )
            else:
                routing_code = routing_code.replace(
                    "const routes: Routes = [",
                    f"const routes: Routes = [\n  {route_entry},"
                )

        return routing_code