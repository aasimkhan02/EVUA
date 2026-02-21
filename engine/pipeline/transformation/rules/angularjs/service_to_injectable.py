from pathlib import Path
from ir.migration_model.change import Change
from ir.migration_model.base import ChangeSource
from pipeline.transformation.angular_project_scaffold import AngularProjectScaffold
from pipeline.transformation.helpers import iter_services


class ServiceToInjectableRule:
    def __init__(self, out_dir="out/angular-app"):
        self.project = AngularProjectScaffold(out_dir)
        self.out_dir = Path(out_dir) / "src" / "app"

    def apply(self, analysis, patterns):
        print("\n========== ServiceToInjectableRule.apply() ==========")
        changes = []
        self.project.ensure()

        # iter_services yields ir.code_model.class_.Class nodes
        # Class has: .id (uuid str), .name (str)
        services = list(iter_services(analysis, patterns))
        print(f"[ServiceToInjectable] Services detected: {len(services)}")

        if not services:
            print("[ServiceToInjectable] ⚠️  No services matched. "
                  "Check SemanticRole.SERVICE in patterns or class names ending with 'Service'/'Svc'.")

        for node in services:
            # node.name is guaranteed by ir.code_model.class_.Class
            raw_name = node.name
            base = raw_name.replace("Service", "").replace("Svc", "")
            class_name = base + "Service"
            file_name  = f"{class_name.lower()}.service.ts"
            ts_path    = self.out_dir / file_name

            ts_code = (
                f"import {{ Injectable }} from '@angular/core';\n\n"
                f"@Injectable({{\n"
                f"  providedIn: 'root'\n"
                f"}})\n"
                f"export class {class_name} {{\n"
                f"  // TODO: migrate service logic here\n"
                f"}}\n"
            )

            if not ts_path.exists() or ts_path.read_text(encoding="utf-8") != ts_code:
                ts_path.parent.mkdir(parents=True, exist_ok=True)
                ts_path.write_text(ts_code, encoding="utf-8")
                print(f"[ServiceToInjectable] ✅ Written: {ts_path}")

            # node.id is the uuid from IRNode — valid Change.before_id
            changes.append(Change(
                before_id=node.id,
                after_id="injectable_" + node.id,
                source=ChangeSource.RULE,
                reason=f"Service → @Injectable(providedIn: 'root') at {ts_path}"
            ))

        print("========== ServiceToInjectableRule DONE ==========\n")
        return changes