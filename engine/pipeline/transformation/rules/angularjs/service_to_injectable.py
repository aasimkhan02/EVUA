from pathlib import Path
from ir.migration_model.change import Change
from ir.migration_model.base import ChangeSource
from pipeline.patterns.roles import SemanticRole
from pipeline.transformation.angular_project_scaffold import AngularProjectScaffold

class ServiceToInjectableRule:
    def __init__(self, out_dir="out/angular-app"):
        self.project = AngularProjectScaffold(out_dir)
        self.out_dir = Path(out_dir) / "src" / "app"

    def apply(self, analysis, patterns):
        changes = []
        self.project.ensure()

        for node_id, roles in patterns.roles_by_node.items():
            if SemanticRole.SERVICE not in roles:
                continue

            name = f"MigratedService{node_id[:6]}"
            file_name = f"{name.lower()}.service.ts"
            ts_path = self.out_dir / file_name

            if not ts_path.exists():
                ts_code = f"""
import {{ Injectable }} from '@angular/core';

@Injectable({{
  providedIn: 'root'
}})
export class {name} {{
  // TODO: migrate service logic manually if behavior depends on $http/$q side-effects
}}
""".strip()
                ts_path.write_text(ts_code)

            changes.append(
                Change(
                    before_id=node_id,
                    after_id="injectable_" + node_id,
                    source=ChangeSource.RULE,
                    reason=f"Service → @Injectable() wired into Angular app at {self.project.root} (file: {ts_path})"
                )
            )

        return changes
