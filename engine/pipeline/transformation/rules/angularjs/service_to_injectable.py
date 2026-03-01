from pathlib import Path
from ir.migration_model.change import Change
from ir.migration_model.base import ChangeSource
from pipeline.transformation.angular_project_scaffold import AngularProjectScaffold
from pipeline.transformation.helpers import iter_services
from pipeline.transformation.di_mapper import resolve_di_tokens
from collections import defaultdict


def _build_service_ts(class_name: str, raw_name: str, di_tokens: list[str]) -> str:
    """
    Generate Angular @Injectable with a typed constructor from AngularJS DI tokens.
    """
    resolution = resolve_di_tokens(di_tokens)

    imports_by_module: dict[str, list[str]] = defaultdict(list)
    imports_by_module["@angular/core"].append("Injectable")

    for symbol, module in resolution.imports:
        if symbol not in imports_by_module[module]:
            imports_by_module[module].append(symbol)

    custom_params: list[str] = []
    for svc_token in resolution.custom_services:
        svc_class = svc_token
        svc_param = svc_class[0].lower() + svc_class[1:]
        svc_file  = f"./{svc_token.lower()}.service"
        imports_by_module[svc_file].append(svc_class)
        custom_params.append(f"private {svc_param}: {svc_class}")

    import_lines: list[str] = []
    angular_modules = sorted(k for k in imports_by_module if k.startswith("@"))
    local_modules   = sorted(k for k in imports_by_module if not k.startswith("@"))
    for mod in angular_modules + local_modules:
        symbols = imports_by_module[mod]
        import_lines.append(f"import {{ {', '.join(symbols)} }} from '{mod}';")

    all_params = resolution.constructor_params + custom_params
    if all_params:
        param_str = ", ".join(all_params)
        if len(param_str) > 72:
            inner = ",\n    ".join(all_params)
            ctor  = f"  constructor(\n    {inner}\n  ) {{}}"
        else:
            ctor = f"  constructor({param_str}) {{}}"
    else:
        ctor = None

    comment_lines: list[str] = []
    for comment in resolution.comments:
        comment_lines.append(f"  // {comment}")

    lines: list[str] = import_lines
    lines.append("")
    lines.append("@Injectable({")
    lines.append("  providedIn: 'root'")
    lines.append("})")
    lines.append(f"export class {class_name} {{")
    lines.append(f"  // TODO: migrate service logic from AngularJS {raw_name}")

    if comment_lines:
        lines.extend(comment_lines)
    if ctor:
        lines.append(ctor)

    lines.append("}")
    lines.append("")

    return "\n".join(lines)


class ServiceToInjectableRule:
    def __init__(self, out_dir: str = "out/angular-app", dry_run: bool = False):
        self.project  = AngularProjectScaffold(out_dir)
        self.out_dir  = Path(out_dir) / "src" / "app"
        self.dry_run  = dry_run

    def apply(self, analysis, patterns):
        print("\n========== ServiceToInjectableRule.apply() ==========")
        if self.dry_run:
            print("[ServiceToInjectable] DRY RUN — no files will be written")

        changes = []

        if not self.dry_run:
            self.project.ensure()

        services = list(iter_services(analysis, patterns))
        print(f"[ServiceToInjectable] Services detected: {len(services)}")

        for node in services:
            raw_name = node.name
            di_tokens: list[str] = getattr(node, "di", [])

            if raw_name.lower().endswith("service") or raw_name.lower().endswith("svc"):
                base       = raw_name.replace("Service", "").replace("Svc", "")
                class_name = base + "Service"
            elif raw_name.lower().endswith("factory"):
                class_name = raw_name
                base       = raw_name
            else:
                class_name = raw_name + "Service"
                base       = raw_name

            file_name = f"{raw_name.lower()}.service.ts"
            ts_path   = self.out_dir / file_name

            if di_tokens:
                print(f"[ServiceToInjectable] DI for {raw_name}: {di_tokens}")

            ts_code = _build_service_ts(class_name, raw_name, di_tokens)

            if self.dry_run:
                print(f"[DRY RUN] Would write: {ts_path}")
                print(f"[DRY RUN] Content preview:\n{ts_code[:300]}")
            else:
                if not ts_path.exists() or ts_path.read_text(encoding="utf-8") != ts_code:
                    ts_path.parent.mkdir(parents=True, exist_ok=True)
                    ts_path.write_text(ts_code, encoding="utf-8")
                    print(f"[ServiceToInjectable] Written: {ts_path}")

            changes.append(Change(
                before_id=node.id,
                after_id="injectable_" + node.id,
                source=ChangeSource.RULE,
                reason=f"Service → @Injectable(providedIn: 'root') at {ts_path}"
            ))

        print("========== ServiceToInjectableRule DONE ==========\n")
        return changes