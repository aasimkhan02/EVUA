from pathlib import Path
from ir.migration_model.change import Change
from ir.migration_model.base import ChangeSource
from pipeline.patterns.roles import SemanticRole
from pipeline.transformation.angular_project_scaffold import AngularProjectScaffold

UNSAFE_ROLES = {
    SemanticRole.TEMPLATE_BINDING,  # proxy for directives / transclusion
}

class ControllerToComponentRule:
    def __init__(self, out_dir="out/angular-app"):
        self.project = AngularProjectScaffold(out_dir)
        self.out_dir = Path(out_dir) / "src" / "app"

    def apply(self, analysis, patterns):
        changes = []
        self.project.ensure()

        app_module_path = self.out_dir / "app.module.ts"
        app_module_code = app_module_path.read_text()

        routes_injected = "component:" in app_module_code

        for m in analysis.modules:
            for c in m.classes:
                # ✅ Only real controllers
                if not c.name.lower().endswith("controller"):
                    continue

                roles = patterns.roles_by_node.get(c.id, [])

                if SemanticRole.CONTROLLER not in roles:
                    continue

                # 🚨 Unsafe edge-cases → emit manual stub instead of auto-migrate
                if any(r in roles for r in UNSAFE_ROLES):
                    changes.append(
                        Change(
                            before_id=c.id,
                            after_id=f"manual_component_{c.id}",
                            source=ChangeSource.RULE,
                            reason=(
                                "Controller uses unsafe AngularJS features "
                                "(directives/transclusion/$compile/nested scopes/deep $watch). "
                                "Manual migration required."
                            ),
                        )
                    )
                    continue

                base = c.name.replace("Controller", "").lower()
                class_name = c.name.replace("Controller", "") + "Component"

                ts_path = self.out_dir / f"{base}.component.ts"
                html_path = self.out_dir / f"{base}.component.html"

                ts_code = f"""
import {{ Component }} from '@angular/core';

@Component({{
  selector: 'app-{base}',
  templateUrl: './{base}.component.html'
}})
export class {class_name} {{}}
""".strip()

                html_code = f"<h2>{class_name}</h2>"

                ts_path.write_text(ts_code)
                html_path.write_text(html_code)

                import_line = f"import {{ {class_name} }} from './{base}.component';"
                if import_line not in app_module_code:
                    app_module_code = import_line + "\n" + app_module_code

                if class_name not in app_module_code:
                    app_module_code = app_module_code.replace(
                        "declarations: [AppComponent]",
                        f"declarations: [AppComponent, {class_name}]"
                    )

                if not routes_injected:
                    app_module_code = app_module_code.replace(
                        "const routes: Routes = [];",
                        f"const routes: Routes = [{{ path: '', component: {class_name} }}];"
                    )
                    routes_injected = True

                changes.append(
                    Change(
                        before_id=c.id,
                        after_id=f"component_{c.id}",
                        source=ChangeSource.RULE,
                        reason=(
                            f"Controller → Angular Component wired into Angular app at "
                            f"{self.project.root} (files: {ts_path}, {html_path})"
                        )
                    )
                )

        app_module_path.write_text(app_module_code)
        return changes
