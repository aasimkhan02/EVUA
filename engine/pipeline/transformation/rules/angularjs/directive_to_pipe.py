from pathlib import Path
from pipeline.patterns.roles import SemanticRole
from pipeline.transformation.helpers import iter_nodes_with_role
from ir.migration_model.change import Change


class DirectiveToPipeRule:
    def __init__(self, out_dir: Path, dry_run: bool = False):
        self.out_dir = Path(out_dir)
        self.app_dir = self.out_dir / "src" / "app"
        self.dry_run = dry_run

    def apply(self, analysis, patterns):
        changes = []

        for directive in iter_nodes_with_role(analysis, patterns, SemanticRole.DIRECTIVE):
            name = directive.name

            # Attribute-only directives → pipe
            restrict = getattr(directive, "restrict", "")
            if "A" not in restrict or "E" in restrict:
                continue

            base = name.replace("Directive", "").lower()
            ts_path = self.app_dir / f"{base}.pipe.ts"

            ts_code = f"""import {{ Pipe, PipeTransform }} from '@angular/core';

@Pipe({{
  name: '{base}'
}})
export class {name}Pipe implements PipeTransform {{
  transform(value: any, ...args: any[]): any {{
    // TODO: migrate directive behavior manually
    return value;
  }}
}}
"""

            if not self.dry_run:
                self.app_dir.mkdir(parents=True, exist_ok=True)
                ts_path.write_text(ts_code, encoding="utf-8")

            changes.append(Change(
                before_id=directive.id,
                after_id=directive.id,
                description=f"Directive {name} migrated to Angular Pipe",
                source="RULE"
            ))

        return changes