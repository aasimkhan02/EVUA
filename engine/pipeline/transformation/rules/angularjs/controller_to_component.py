from pathlib import Path
from ir.migration_model.change import Change
from ir.migration_model.base import ChangeSource
from pipeline.patterns.roles import SemanticRole

class ControllerToComponentRule:
    def __init__(self, out_dir="out/angular"):
        self.out_dir = Path(out_dir)

    def apply(self, analysis, patterns):
        changes = []
        self.out_dir.mkdir(parents=True, exist_ok=True)

        for m in analysis.modules:
            for c in m.classes:
                roles = patterns.roles_by_node.get(c.id, [])
                if SemanticRole.CONTROLLER in roles:
                    base_name = c.name.replace("Controller", "").lower()
                    class_name = c.name.replace("Controller", "") + "Component"

                    ts_path = self.out_dir / f"{base_name}.component.ts"
                    html_path = self.out_dir / f"{base_name}.component.html"

                    ts_code = f"""
import {{ Component }} from '@angular/core';

@Component({{
  selector: 'app-{base_name}',
  templateUrl: './{base_name}.component.html'
}})
export class {class_name} {{
  // TODO: migrate state and methods from $scope
}}
""".strip()

                    html_code = f"""
<!-- TODO: migrate template bindings -->
<div>
  <h2>{class_name}</h2>
</div>
""".strip()

                    ts_path.write_text(ts_code)
                    html_path.write_text(html_code)

                    changes.append(
                        Change(
                            before_id=c.id,
                            after_id=f"component_{c.id}",
                            source=ChangeSource.RULE,
                            reason=f"Controller → Angular Component written to {ts_path}",
                        )
                    )

        return changes
