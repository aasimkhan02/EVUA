from pathlib import Path
from ir.migration_model.change import Change
from ir.migration_model.base import ChangeSource
from pipeline.patterns.roles import SemanticRole
from pipeline.transformation.angular_project_scaffold import AngularProjectScaffold
from pipeline.transformation.helpers import iter_shallow_watches, resolve_owner_class

RXJS_IMPORT = "import { BehaviorSubject } from 'rxjs';\n"


class SimpleWatchToRxjsRule:
    def __init__(self, out_dir="out/angular-app"):
        self.project = AngularProjectScaffold(out_dir)
        self.app_dir = Path(out_dir) / "src" / "app"

    def apply(self, analysis, patterns):
        print("\n========== SimpleWatchToRxjsRule.apply() ==========")
        changes = []
        self.project.ensure()

        # Track which component files we've already injected into
        # so that multiple Observer nodes pointing to the same class
        # don't inject BehaviorSubject twice (fixes duplicate injection bug)
        injected_files: set = set()

        watches = list(iter_shallow_watches(analysis, patterns))
        print(f"[SimpleWatchToRxjs] Shallow watches detected: {len(watches)}")

        if not watches:
            print("[SimpleWatchToRxjs] ⚠️  No shallow watches matched. "
                  "Check SemanticRole.SHALLOW_WATCH in patterns or analysis.watches.")

        for node in watches:
            node_id = getattr(node, "id", str(id(node)))

            # Observer has .observed_symbol_id, NOT .name
            # We find the owning Class to derive the component filename
            owner = resolve_owner_class(analysis, node_id)

            # Fallback: try observed_symbol_id to find the owner
            if owner is None:
                sym_id = getattr(node, "observed_symbol_id", None)
                if sym_id:
                    owner = resolve_owner_class(analysis, sym_id)

            if owner is None:
                print(f"[SimpleWatchToRxjs] ℹ️  Cannot resolve owner class for watch {node_id}, skipping injection")
            else:
                base = (
                    owner.name
                    .replace("Controller", "")
                    .replace("Ctrl", "")
                    .lower()
                )
                component_ts = self.app_dir / f"{base}.component.ts"

                if component_ts not in injected_files:
                    self._inject_behavior_subject(component_ts, base)
                    injected_files.add(component_ts)
                else:
                    print(f"[SimpleWatchToRxjs] ℹ️  Already injected into {component_ts.name}, skipping duplicate")

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
            print(f"[SimpleWatchToRxjs] ℹ️  Component file not found, skipping: {component_ts}")
            return

        text = component_ts.read_text(encoding="utf-8")

        if RXJS_IMPORT not in text:
            text = RXJS_IMPORT + text

        subject_prop = f"  {base}$ = new BehaviorSubject<any>(null);"
        if subject_prop not in text:
            # Inject right after the first class opening brace
            idx = text.find("{")
            if idx != -1:
                text = text[: idx + 1] + f"\n{subject_prop}\n" + text[idx + 1:]

        component_ts.write_text(text, encoding="utf-8")
        print(f"[SimpleWatchToRxjs] ✅ BehaviorSubject injected into: {component_ts}")