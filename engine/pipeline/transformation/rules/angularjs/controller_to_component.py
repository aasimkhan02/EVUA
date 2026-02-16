from pathlib import Path
from ir.migration_model.change import Change
from ir.migration_model.base import ChangeSource
from pipeline.patterns.roles import SemanticRole
from pipeline.transformation.angular_project_scaffold import AngularProjectScaffold

UNSAFE_ROLES = {
    SemanticRole.TEMPLATE_BINDING,
}

class ControllerToComponentRule:
    def __init__(self, out_dir="out/angular-app"):
        self.project = AngularProjectScaffold(out_dir)
        self.out_dir = Path(out_dir) / "src" / "app"
        self.routing_path = self.out_dir / "app-routing.module.ts"

    def _ensure_routing_module(self):
        self.routing_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.routing_path.exists():
            self.routing_path.write_text(
                """import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

const routes: Routes = [];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule {}
""",
                encoding="utf-8"
            )

    def apply(self, analysis, patterns):
        changes = []
        self.project.ensure()
        self._ensure_routing_module()

        routing_code = self.routing_path.read_text(encoding="utf-8")

        # collect migrated services for DI
        service_names = []
        for node_id, roles in patterns.roles_by_node.items():
            if SemanticRole.SERVICE in roles:
                service_names.append(f"MigratedService{node_id[:6]}")

        for m in analysis.modules:
            for c in m.classes:
                if not c.name.lower().endswith("controller"):
                    continue

                roles = patterns.roles_by_node.get(c.id, [])
                if SemanticRole.CONTROLLER not in roles:
                    continue

                if any(r in roles for r in UNSAFE_ROLES):
                    changes.append(
                        Change(
                            before_id=c.id,
                            after_id=f"manual_component_{c.id}",
                            source=ChangeSource.RULE,
                            reason="Unsafe AngularJS semantics detected; manual migration required.",
                        )
                    )
                    continue

                base = c.name.replace("Controller", "").lower()
                class_name = c.name.replace("Controller", "") + "Component"
                selector = f"app-{base}"

                ts_path = self.out_dir / f"{base}.component.ts"
                html_path = self.out_dir / f"{base}.component.html"

                imports = ["import { Component } from '@angular/core';"]
                ctor_params = []

                for svc in service_names:
                    imports.append(f"import {{ {svc} }} from './{svc.lower()}.service';")
                    ctor_params.append(f"private {svc[0].lower() + svc[1:]}: {svc}")

                ctor_block = ""
                if ctor_params:
                    ctor_block = f"\n  constructor({', '.join(ctor_params)}) {{}}\n"

                ts_code = f"""\
{chr(10).join(imports)}

@Component({{
  selector: '{selector}',
  templateUrl: './{base}.component.html'
}})
export class {class_name} {{{ctor_block}}}
""".strip()

                ts_path.write_text(ts_code, encoding="utf-8")
                html_path.write_text(f"<h2>{class_name}</h2>", encoding="utf-8")

                import_line = f"import {{ {class_name} }} from './{base}.component';"
                if import_line not in routing_code:
                    routing_code = import_line + "\n" + routing_code

                route_entry = f"{{ path: '{base}', component: {class_name} }}"
                if route_entry not in routing_code:
                    routing_code = routing_code.replace(
                        "const routes: Routes = [];",
                        f"const routes: Routes = [\n  {route_entry}\n];"
                    )

                changes.append(
                    Change(
                        before_id=c.id,
                        after_id=f"component_{c.id}",
                        source=ChangeSource.RULE,
                        reason=f"Controller → Angular Component wired + routed at /{base} (DI ready)",
                    )
                )

        self.routing_path.write_text(routing_code, encoding="utf-8")
        return changes
