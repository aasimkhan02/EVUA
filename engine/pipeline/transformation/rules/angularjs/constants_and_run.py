"""
pipeline/transformation/rules/angularjs/constants_and_run.py

ConstantsAndRunRule
===================
Handles two AngularJS patterns that have no direct Angular equivalent:

1. .constant('KEY', value) / .value('KEY', value)
   → Generates src/app/app-constants.ts with export const declarations
     and InjectionToken entries for use in Angular DI.

2. .run([...deps, fn])
   → Generates src/app/app-init.service.ts with an APP_INITIALIZER stub
     containing the original run block body as a TODO comment.

Both files are only generated if the corresponding patterns are detected.
"""

from pathlib import Path
from ir.migration_model.change import Change
from ir.migration_model.base import ChangeSource
from pipeline.transformation.angular_project_scaffold import AngularProjectScaffold


def _build_constants_ts(constants: list) -> str:
    """
    Generate app-constants.ts from a list of RawConstant objects.

    Each constant becomes:
      export const API_BASE_URL = 'https://...';
      export const API_BASE_URL_TOKEN = new InjectionToken<string>('API_BASE_URL');
    """
    lines = [
        "import { InjectionToken } from '@angular/core';",
        "",
        "// Auto-generated from AngularJS .constant() / .value() registrations.",
        "// Review and add proper TypeScript types where marked TODO.",
        "",
    ]

    for c in constants:
        name      = c.name
        raw_val   = c.raw_value.strip()
        kind      = c.kind  # 'constant' or 'value'
        comment   = "// AngularJS ." + kind + "('" + name + "', ...)"
        lines.append(comment)
        lines.append(f"export const {name} = {raw_val};")
        lines.append(f"export const {name}_TOKEN = new InjectionToken<any>('{name}');")
        lines.append("")

    return "\n".join(lines)


def _build_run_block_ts(run_blocks: list) -> str:
    """
    Generate app-init.service.ts from a list of RawRunBlock objects.
    Uses Angular's APP_INITIALIZER multi-provider pattern.
    """
    lines = [
        "import { APP_INITIALIZER, NgModule } from '@angular/core';",
        "",
        "// Auto-generated from AngularJS .run() block(s).",
        "// The original run block logic is preserved as TODO comments below.",
        "// Migrate to an Angular service + APP_INITIALIZER provider.",
        "//",
        "// Example wiring in AppModule:",
        "//   providers: [",
        "//     { provide: APP_INITIALIZER, useFactory: appInitFactory, multi: true }",
        "//   ]",
        "",
        "export function appInitFactory(): () => void {",
        "  return () => {",
        "    console.log(\"init\");",
    ]

    for i, rb in enumerate(run_blocks):
        lines.append(f"    // --- Run block {i + 1} (DI: {rb.di}) ---")
        for src_line in (rb.body_src or "// (empty body)").splitlines():
            lines.append(f"    // {src_line}")

    lines += [
        "  };",
        "}",
        "",
    ]

    return "\n".join(lines)


class ConstantsAndRunRule:
    """
    Generates app-constants.ts and app-init.service.ts from AngularJS
    .constant()/.value() and .run() block registrations.
    """

    def __init__(self, out_dir: str = "out/angular-app", dry_run: bool = False):
        self.project  = AngularProjectScaffold(out_dir)
        self.app_dir  = Path(out_dir) / "src" / "app"
        self.dry_run  = dry_run

    def apply(self, analysis, patterns):
        print("\n========== ConstantsAndRunRule.apply() ==========")
        changes = []

        if not self.dry_run:
            self.project.ensure()

        # Get raw_constants and raw_run_blocks from the JS analyzer output
        # They are stored on the JSAnalyzer instance via self.raw_constants etc.
        # The analysis object aggregates them from all analyzers.
        raw_constants  = getattr(analysis, "raw_constants",  []) or []
        raw_run_blocks = getattr(analysis, "raw_run_blocks", []) or []

        print(f"[ConstantsAndRun] Constants detected: {len(raw_constants)}")
        print(f"[ConstantsAndRun] Run blocks detected: {len(raw_run_blocks)}")

        # ── Generate app-constants.ts ──────────────────────────────────────
        if raw_constants:
            ts_code   = _build_constants_ts(raw_constants)
            ts_path   = self.app_dir / "app-constants.ts"
            if self.dry_run:
                print(f"[DRY RUN] Would write: {ts_path}")
                print(f"[DRY RUN] Preview:\n{ts_code[:300]}")
            else:
                ts_path.parent.mkdir(parents=True, exist_ok=True)
                ts_path.write_text(ts_code, encoding="utf-8")
                print(f"[ConstantsAndRun] Written: {ts_path}")
            changes.append(Change(
                before_id="constants_stub",
                after_id="app_constants_ts",
                source=ChangeSource.RULE,
                reason=f"Generated app-constants.ts with {len(raw_constants)} constants/values",
            ))

        # ── Generate app-init.service.ts ──────────────────────────────────
        if raw_run_blocks:
            ts_code = _build_run_block_ts(raw_run_blocks)
            ts_path = self.app_dir / "app-init.service.ts"
            if self.dry_run:
                print(f"[DRY RUN] Would write: {ts_path}")
                print(f"[DRY RUN] Preview:\n{ts_code[:300]}")
            else:
                ts_path.parent.mkdir(parents=True, exist_ok=True)
                ts_path.write_text(ts_code, encoding="utf-8")
                print(f"[ConstantsAndRun] Written: {ts_path}")
            changes.append(Change(
                before_id="run_block_stub",
                after_id="app_init_service_ts",
                source=ChangeSource.RULE,
                reason=f"Generated app-init.service.ts from {len(raw_run_blocks)} .run() block(s)",
            ))

        print("========== ConstantsAndRunRule DONE ==========\n")
        return changes
