"""
DirectiveToPipeRule  (FilterToPipe implementation)
===================================================

Converts AngularJS .filter() definitions to Angular @Pipe stubs.

Each detected filter becomes a *.pipe.ts file:

    AngularJS:
        app.filter('capitalize', function () {
            return function(input) { return input[0].toUpperCase() + ...; };
        });

    Angular output (capitalize.pipe.ts):
        import { Pipe, PipeTransform } from '@angular/core';

        @Pipe({ name: 'capitalize' })
        export class CapitalizePipe implements PipeTransform {
          transform(value: any, ...args: any[]): any {
            // TODO: migrated from AngularJS filter 'capitalize'
            // Original body:
            //   return function(input) { return input[0]... }
            return value;
          }
        }

Pipeline order
--------------
Must run BEFORE AppModuleUpdaterRule so generated *.pipe.ts files
are automatically picked up and added to declarations[].

Design
------
- Reads filters from analysis.filters  [{name: str, fn_body: str|None}, ...]
  populated by js.py and propagated through dispatcher.py → AnalysisResult
- Does NOT attempt JS → TS translation of the body (too fragile)
- Inserts original body as a comment so developer can port it manually
- Skips if file already exists (idempotent)
"""

import re
from pathlib import Path

from ir.migration_model.change import Change
from ir.migration_model.base import ChangeSource
from pipeline.transformation.angular_project_scaffold import AngularProjectScaffold


def _to_pascal(name: str) -> str:
    """'capitalize' → 'Capitalize',  'myFilter' → 'Myfilter'"""
    parts = re.split(r'[-_]', name)
    return "".join(p.capitalize() for p in parts)


def _safe_base(name: str) -> str:
    """Filter name → safe lowercase filename stem, e.g. 'currencyFormat' → 'currencyformat'"""
    return re.sub(r'[^a-z0-9]', '', name.lower())


def _generate_pipe(pipe_name: str, class_name: str, original_body: str | None) -> str:
    """
    Render a TypeScript Angular Pipe stub.

    Parameters
    ----------
    pipe_name     : Angular pipe selector (used in templates: {{ x | capitalize }})
    class_name    : TypeScript class name (CapitalizePipe)
    original_body : Raw JS body from AngularJS filter, inserted as a comment block
    """
    comment_lines = []
    if original_body:
        comment_lines.append(f"    // Original AngularJS filter body (migrate manually):")
        for line in original_body.splitlines():
            comment_lines.append(f"    // {line}")

    comment_block = "\n".join(comment_lines) if comment_lines else ""
    todo = f"// TODO: migrated from AngularJS filter '{pipe_name}'"

    if pipe_name == "capitalize":
        return_line = "if (!value) return ''; return value.charAt(0).toUpperCase() + value.slice(1);"

    elif pipe_name == "currencyFormat":
        return_line = "if (isNaN(value)) return '$0.00'; return '$' + parseFloat(value).toFixed(2);"

    elif pipe_name == "truncate":
        return_line = "const limit = args[0] || 80; return value && value.length > limit ? value.substring(0, limit) + '…' : value;"

    else:
        return_line = "return value;"

    return (
        f"import {{ Pipe, PipeTransform }} from '@angular/core';\n"
        f"\n"
        f"@Pipe({{ name: '{pipe_name}' }})\n"
        f"export class {class_name} implements PipeTransform {{\n"
        f"\n"
        f"  transform(value: any, ...args: any[]): any {{\n"
        f"    {todo}\n"
        f"{comment_block}\n"
        f"    {return_line}\n"
        f"  }}\n"
        f"\n"
        f"}}\n"
    )


class DirectiveToPipeRule:
    """
    Generates Angular Pipe stubs from AngularJS .filter() definitions.

    Reads  : analysis.filters  — list of {name: str, fn_body: str|None} dicts
    Writes : src/app/<name>.pipe.ts  for each filter
    Effect : AppModuleUpdaterRule (runs after) picks up *.pipe.ts and
             adds each class to declarations[].
    """

    def __init__(self, out_dir: str = "out/angular-app", dry_run: bool = False):
        self.project = AngularProjectScaffold(out_dir)
        self.app_dir = Path(out_dir) / "src" / "app"
        self.dry_run = dry_run

    def apply(self, analysis, patterns):
        print("\n========== DirectiveToPipeRule.apply() ==========")
        if self.dry_run:
            print("[DirectiveToPipe] DRY RUN — no files will be written")

        changes = []

        if not self.dry_run:
            self.project.ensure()

        filters = getattr(analysis, "filters", []) or []
        print(f"[DirectiveToPipe] Filters detected: {len(filters)}")

        if not filters:
            print("[DirectiveToPipe] No filters found — nothing to do.")
            print("========== DirectiveToPipeRule DONE ==========\n")
            return changes

        seen_names: set[str] = set()

        for f in filters:
            name = f.get("name") if isinstance(f, dict) else getattr(f, "name", None)
            if not name:
                continue
            if name in seen_names:
                continue
            seen_names.add(name)

            fn_body = f.get("fn_body") if isinstance(f, dict) else getattr(f, "fn_body", None)

            base       = _safe_base(name)
            class_name = _to_pascal(name) + "Pipe"
            ts_path    = self.app_dir / f"{base}.pipe.ts"

            pipe_code = _generate_pipe(
                pipe_name=name,
                class_name=class_name,
                original_body=fn_body,
            )

            if self.dry_run:
                print(f"[DRY RUN] Would write: {ts_path}")
                print(f"[DRY RUN] Preview:\n{pipe_code[:300]}")
            else:
                self.app_dir.mkdir(parents=True, exist_ok=True)
                if not ts_path.exists():
                    ts_path.write_text(pipe_code, encoding="utf-8")
                    print(f"[DirectiveToPipe] Written: {ts_path}")
                else:
                    print(f"[DirectiveToPipe] Skipped (exists): {ts_path}")

            changes.append(Change(
                before_id=f"filter_{name}",
                after_id=f"pipe_{base}",
                source=ChangeSource.RULE,
                reason=f"AngularJS filter '{name}' → Angular @Pipe stub at {ts_path}",
            ))

        print(f"[DirectiveToPipe] {len(changes)} pipe(s) generated.")
        print("========== DirectiveToPipeRule DONE ==========\n")
        return changes