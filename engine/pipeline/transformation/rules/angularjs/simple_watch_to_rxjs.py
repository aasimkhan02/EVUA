from pathlib import Path
from ir.migration_model.change import Change
from ir.migration_model.base import ChangeSource
from pipeline.patterns.roles import SemanticRole
from pipeline.transformation.angular_project_scaffold import AngularProjectScaffold
from pipeline.transformation.helpers import iter_shallow_watches, resolve_owner_class
import re

RXJS_IMPORT = "import { BehaviorSubject } from 'rxjs';\n"


def _find_class_body_start(text: str) -> int:
    """
    Return the index of the '{' that opens a TypeScript class body.

    Strategy: find 'export class <Name>' or 'class <Name>' then scan
    forward for the first '{' after that — skipping any decorator
    or import braces that appear earlier in the file.

    Returns -1 if no class declaration is found.
    """
    class_decl = re.search(r'\bclass\s+\w+', text)
    if not class_decl:
        return -1

    # The class body '{' is the first '{' at or after the class declaration
    brace_pos = text.find("{", class_decl.end())
    return brace_pos


class SimpleWatchToRxjsRule:
    def __init__(self, out_dir: str = "out/angular-app", dry_run: bool = False):
        self.project  = AngularProjectScaffold(out_dir)
        self.app_dir  = Path(out_dir) / "src" / "app"
        self.dry_run  = dry_run

    def apply(self, analysis, patterns):
        print("\n========== SimpleWatchToRxjsRule.apply() ==========")
        if self.dry_run:
            print("[SimpleWatchToRxjs] DRY RUN — no files will be written")

        changes = []

        if not self.dry_run:
            self.project.ensure()

        # Track injected files to avoid duplicate BehaviorSubject fields
        injected_files: set = set()

        watches = list(iter_shallow_watches(analysis, patterns))
        print(f"[SimpleWatchToRxjs] Shallow watches detected: {len(watches)}")

        if not watches:
            print("[SimpleWatchToRxjs]  No shallow watches matched.")

        for node in watches:
            node_id = getattr(node, "id", str(id(node)))

            owner = resolve_owner_class(analysis, node_id)
            if owner is None:
                sym_id = getattr(node, "observed_symbol_id", None)
                if sym_id:
                    owner = resolve_owner_class(analysis, sym_id)

            if owner is None:
                print(f"[SimpleWatchToRxjs]  Cannot resolve owner for watch {node_id}, skipping")
            else:
                base = (
                    owner.name
                    .replace("Controller", "")
                    .replace("Ctrl", "")
                    .lower()
                )
                component_ts = self.app_dir / f"{base}.component.ts"

                if component_ts not in injected_files:
                    if not self.dry_run:
                        self._inject_behavior_subject(component_ts, base)
                    else:
                        print(f"[DRY RUN] Would inject BehaviorSubject into: {component_ts}")
                    injected_files.add(component_ts)
                else:
                    print(f"[SimpleWatchToRxjs]  Already injected {component_ts.name}, skipping duplicate")

            changes.append(Change(
                before_id=node_id,
                after_id=f"rx_{node_id}",
                source=ChangeSource.RULE,
                reason="Shallow $watch → RxJS BehaviorSubject rewrite",
            ))

        print("========== SimpleWatchToRxjsRule DONE ==========\n")
        return changes

    def _inject_behavior_subject(self, component_ts: Path, base: str):
        if not component_ts.exists():
            print(f"[SimpleWatchToRxjs]  Component file not found, skipping: {component_ts}")
            return

        text = component_ts.read_text(encoding="utf-8")

        # ── Add RxJS import if missing ────────────────────────────────────
        if RXJS_IMPORT not in text:
            # Insert after the last existing import line to keep imports grouped
            last_import = None
            for m in re.finditer(r'^import\s+.+;\s*$', text, re.MULTILINE):
                last_import = m
            if last_import:
                insert_at = last_import.end()
                text = text[:insert_at] + "\n" + RXJS_IMPORT + text[insert_at:]
            else:
                text = RXJS_IMPORT + text

        # ── Inject BehaviorSubject field into class body ──────────────────
        subject_prop = f"  {base}$ = new BehaviorSubject<any>(null);"
        if subject_prop not in text:
            brace_idx = _find_class_body_start(text)
            if brace_idx != -1:
                text = text[:brace_idx + 1] + f"\n{subject_prop}\n" + text[brace_idx + 1:]
            else:
                print(f"[SimpleWatchToRxjs]  Could not find class body in {component_ts.name}, appending")
                text += f"\n// TODO: add to class body:\n// {subject_prop}\n"

        component_ts.write_text(text, encoding="utf-8")
        print(f"[SimpleWatchToRxjs] BehaviorSubject injected into: {component_ts}")