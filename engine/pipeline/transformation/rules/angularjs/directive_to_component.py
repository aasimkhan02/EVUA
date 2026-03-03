from pathlib import Path
from pipeline.patterns.roles import SemanticRole
from pipeline.transformation.helpers import iter_nodes_with_role
from ir.migration_model.change import Change


class DirectiveToComponentRule:
    def __init__(self, out_dir: Path, dry_run: bool = False):
        self.out_dir = Path(out_dir)
        self.app_dir = self.out_dir / "src" / "app"
        self.dry_run = dry_run

    def apply(self, analysis, patterns):
        changes = []

        for directive in iter_nodes_with_role(analysis, patterns, SemanticRole.DIRECTIVE):
            name = directive.name

            # Element directives only
            restrict = getattr(directive, "restrict", "EA")
            if "E" not in restrict:
                continue

            base = name.replace("Directive", "").lower()
            ts_path = self.app_dir / f"{base}.component.ts"
            html_path = self.app_dir / f"{base}.component.html"

            ts_code = f"""import {{ Component }} from '@angular/core';

@Component({{
  selector: 'app-{base}',
  templateUrl: './{base}.component.html'
}})
export class {name}Component {{
  // TODO: migrate directive logic manually
}}
"""

            html_code = f"""<!-- Migrated from AngularJS directive: {name} -->
<!-- TODO: manual template migration required -->
<div>{name} works</div>
"""

            if not self.dry_run:
                self.app_dir.mkdir(parents=True, exist_ok=True)
                ts_path.write_text(ts_code, encoding="utf-8")
                html_path.write_text(html_code, encoding="utf-8")

            changes.append(Change(
                before_id=directive.id,
                after_id=directive.id,
                description=f"Directive {name} migrated to Angular Component",
                source="RULE"
            ))

        return changes