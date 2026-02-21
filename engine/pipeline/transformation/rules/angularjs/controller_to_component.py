from pathlib import Path
from ir.migration_model.change import Change
from ir.migration_model.base import ChangeSource
from pipeline.transformation.angular_project_scaffold import AngularProjectScaffold
from pipeline.transformation.helpers import iter_controllers


class ControllerToComponentRule:
    def __init__(self, out_dir="out/angular-app"):
        self.project = AngularProjectScaffold(out_dir)
        self.out_dir = Path(out_dir) / "src" / "app"
        self.routing_path = self.out_dir / "app-routing.module.ts"

    def apply(self, analysis, patterns):
        print("\n========== ControllerToComponentRule.apply() ==========")
        changes = []
        self.project.ensure()

        routing_code = self.routing_path.read_text(encoding="utf-8")

        # iter_controllers uses Class.id and Class.name — both confirmed present in IR
        # Module.name is used for debug logging (NOT .path — Module has no .path)
        controllers = list(iter_controllers(analysis, patterns))
        print(f"[ControllerToComponent] Controllers detected: {len(controllers)}")

        if not controllers:
            print("[ControllerToComponent] ⚠️  No controllers matched. "
                  "Check patterns.roles_by_node or Module.classes names.")
            changes.append(Change(
                before_id="debug_controller_rule",
                after_id="debug_controller_rule_ran",
                source=ChangeSource.RULE,
                reason="ControllerToComponentRule ran but matched 0 controllers"
            ))
            return changes

        for c in controllers:
            routing_code = self._emit_component(c, routing_code, changes)

        self.routing_path.write_text(routing_code, encoding="utf-8")
        print("[ControllerToComponent] Routing module updated")
        print("========== ControllerToComponentRule DONE ==========\n")
        return changes

    def _emit_component(self, c, routing_code: str, changes: list) -> str:
        """
        c is ir.code_model.class_.Class — has .id (uuid str) and .name (str).
        """
        base = (
            c.name
            .replace("Controller", "")
            .replace("Ctrl", "")
            .lower()
        )
        class_name = (
            c.name
            .replace("Controller", "")
            .replace("Ctrl", "")
        ) + "Component"
        selector = f"app-{base}"

        ts_path   = self.out_dir / f"{base}.component.ts"
        html_path = self.out_dir / f"{base}.component.html"

        ts_code = (
            f"import {{ Component }} from '@angular/core';\n\n"
            f"@Component({{\n"
            f"  selector: '{selector}',\n"
            f"  templateUrl: './{base}.component.html'\n"
            f"}})\n"
            f"export class {class_name} {{}}\n"
        )

        ts_path.parent.mkdir(parents=True, exist_ok=True)
        if not ts_path.exists() or ts_path.read_text(encoding="utf-8") != ts_code:
            ts_path.write_text(ts_code, encoding="utf-8")
            print(f"[ControllerToComponent] ✅ Written: {ts_path}")

        if not html_path.exists():
            html_path.write_text(f"<h2>{class_name}</h2>\n", encoding="utf-8")

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

        changes.append(Change(
            before_id=c.id,
            after_id=f"component_{c.id}",
            source=ChangeSource.RULE,
            reason=f"Controller → Angular Component written to {ts_path}",
        ))
        return routing_code