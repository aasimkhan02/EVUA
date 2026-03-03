import re
from pathlib import Path
from ir.migration_model.change import Change
from ir.migration_model.base import ChangeSource
from pipeline.transformation.angular_project_scaffold import AngularProjectScaffold
from pipeline.transformation.helpers import iter_controllers
from pipeline.transformation.template_migrator import (
    extract_controller_template,
    migrate_template,
    migrate_template_from_raw,
)
from pipeline.transformation.di_mapper import resolve_di_tokens


def _to_camel(name: str) -> str:
    """Convert a property name to camelCase if it contains underscores."""
    parts = name.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


def _build_component_ts(
    base: str,
    class_name: str,
    selector: str,
    di_tokens: list[str],
    scope_properties: list[str] | None = None,
    scope_methods: list[dict] | None = None,
    init_calls: list[str] | None = None,
    http_calls_by_method: dict[str, list[str]] | None = None,
) -> str:
    """
    Generate the TypeScript component file with:
      - Properly typed constructor (from DI tokens)
      - Class properties migrated from $scope.x = value
      - Class method stubs migrated from $scope.fn = function(...)
      - ngOnInit() that calls startup methods (from top-level $scope.fn() calls)
      - Method bodies that call their own fetch methods
    """
    resolution = resolve_di_tokens(di_tokens)
    scope_properties    = scope_properties    or []
    scope_methods       = scope_methods       or []
    init_calls          = init_calls          or []
    http_calls_by_method = http_calls_by_method or {}

    # ── Collect imports ───────────────────────────────────────────────────
    from collections import defaultdict
    imports_by_module: dict[str, list[str]] = defaultdict(list)
    needs_oninit = bool(init_calls)
    imports_by_module["@angular/core"].append("Component")
    if needs_oninit:
        imports_by_module["@angular/core"].append("OnInit")

    for symbol, module in resolution.imports:
        if symbol not in imports_by_module[module]:
            imports_by_module[module].append(symbol)

    # Custom services
    custom_params: list[str] = []
    for svc_token in resolution.custom_services:
        svc_class = svc_token
        svc_param = svc_class[0].lower() + svc_class[1:]
        svc_file  = f"./{svc_token.lower()}.service"
        imports_by_module[svc_file].append(svc_class)
        custom_params.append(f"private {svc_param}: {svc_class}")

    # Build import lines — @angular/* first, then local
    import_lines: list[str] = []
    angular_modules = sorted(k for k in imports_by_module if k.startswith("@"))
    local_modules   = sorted(k for k in imports_by_module if not k.startswith("@"))
    for mod in angular_modules + local_modules:
        symbols = imports_by_module[mod]
        import_lines.append(f"import {{ {', '.join(symbols)} }} from '{mod}';")

    # ── Constructor ───────────────────────────────────────────────────────
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

    # ── Migration comments ($scope removed, etc.) ─────────────────────────
    comment_lines: list[str] = []
    for comment in resolution.comments:
        comment_lines.append(f"  // {comment}")

    # ── Class properties from $scope.x = value ────────────────────────────
    # Deduplicate preserving order, skip internal $scope props and method names
    method_names = {m["name"] for m in scope_methods}
    seen_props: set[str] = set()
    prop_lines: list[str] = []
    for pname in scope_properties:
        if pname.startswith("$") or pname in method_names or pname in seen_props:
            continue
        seen_props.add(pname)
        prop_lines.append(f"  {pname}: any;  // TODO: add proper type")

    # ── Class methods from $scope.fn = function(...) ──────────────────────
    method_lines: list[str] = []
    seen_methods: set[str] = set()
    for m in scope_methods:
        mname = m["name"]
        if mname.startswith("$") or mname in seen_methods:
            continue
        seen_methods.add(mname)
        params = ", ".join(f"{p}: any" for p in m["params"])
        method_lines.append(f"\n  {mname}({params}): void {{")
        # If this method owns HTTP calls, call the generated fetch methods
        owned_calls = http_calls_by_method.get(mname, [])
        if owned_calls:
            for fetch_fn in owned_calls:
                method_lines.append(f"    this.{fetch_fn}();")
        else:
            method_lines.append(f"    // TODO: migrate from $scope.{mname}")
        method_lines.append(f"  }}")

    # ── ngOnInit from top-level $scope.fn() calls ─────────────────────────
    oninit_lines: list[str] = []
    if init_calls:
        oninit_lines.append("\n  ngOnInit(): void {")
        for call_name in init_calls:
            oninit_lines.append(f"    this.{call_name}();")
        oninit_lines.append("  }")

    # ── Assemble ──────────────────────────────────────────────────────────
    lines: list[str] = import_lines
    lines.append("")
    lines.append("@Component({")
    lines.append(f"  selector: '{selector}',")
    lines.append(f"  templateUrl: './{base}.component.html'")
    lines.append("})")
    implements_clause = " implements OnInit" if needs_oninit else ""
    lines.append(f"export class {class_name}{implements_clause} {{")

    has_body = comment_lines or ctor or prop_lines or method_lines or oninit_lines

    if has_body:
        if prop_lines:
            lines.extend(prop_lines)
            lines.append("")
        if comment_lines:
            lines.extend(comment_lines)
        if ctor:
            lines.append(ctor)
        if method_lines:
            lines.extend(method_lines)
            lines.append("")
        if oninit_lines:
            lines.extend(oninit_lines)
            lines.append("")

    lines.append("}")
    lines.append("")

    return "\n".join(lines)


class ControllerToComponentRule:
    def __init__(self, out_dir: str = "out/angular-app", dry_run: bool = False):
        self.project     = AngularProjectScaffold(out_dir)
        self.out_dir     = Path(out_dir) / "src" / "app"
        self.dry_run     = dry_run
        self._http_calls = []

    def apply(self, analysis, patterns):
        print("\n========== ControllerToComponentRule.apply() ==========")
        if self.dry_run:
            print("[ControllerToComponent] DRY RUN — no files will be written")

        changes = []

        if not self.dry_run:
            self.project.ensure()

        # ── Build template lookup from raw_templates ───────────────────────
        raw_templates = getattr(analysis, "raw_templates", []) or []

        template_html_by_controller: dict[str, str] = {}
        for t in raw_templates:
            ctrl     = getattr(t, "controller", None)
            raw_html = getattr(t, "raw_html", "") or ""
            if ctrl and raw_html.strip():
                template_html_by_controller[ctrl] = raw_html

        # Monolithic index.html: scan for ng-controller references
        for t in raw_templates:
            raw_html = getattr(t, "raw_html", "") or ""
            if not raw_html.strip():
                continue
            for ctrl_match in re.finditer(r'\bng-controller\s*=\s*["\'](\w+)', raw_html):
                ctrl_name = ctrl_match.group(1)
                if ctrl_name not in template_html_by_controller:
                    template_html_by_controller[ctrl_name] = raw_html

        # Store http_calls for use in _emit_component
        self._http_calls = getattr(analysis, "http_calls", []) or []

        controllers = list(iter_controllers(analysis, patterns))
        print(f"[ControllerToComponent] Controllers detected: {len(controllers)}")
        print(f"[ControllerToComponent] Template sources available: {list(template_html_by_controller.keys())}")

        if not controllers:
            print("[ControllerToComponent]  No controllers matched.")
            changes.append(Change(
                before_id="debug_controller_rule",
                after_id="debug_controller_rule_ran",
                source=ChangeSource.RULE,
                reason="ControllerToComponentRule ran but matched 0 controllers"
            ))
            return changes

        for c in controllers:
            source_html  = template_html_by_controller.get(c.name)
            raw_template = next(
                (t for t in raw_templates if getattr(t, "controller", None) == c.name),
                None
            )
            self._emit_component(c, changes, source_html, raw_template)

        print("========== ControllerToComponentRule DONE ==========\n")
        return changes

    # -----------------------------------------------------------------------

    def _resolve_html_content(self, c, source_html, raw_template) -> tuple[str, str]:
        class_name = c.name.replace("Controller", "").replace("Ctrl", "") + "Component"

        if source_html:
            fragment = extract_controller_template(source_html, c.name)
            if fragment:
                content = (
                    f"<!-- Angular template for {class_name} —"
                    f" migrated from AngularJS {c.name} -->\n"
                    + fragment
                )
                return content, "fragment_extracted"

            other_controllers = re.findall(r'\bng-controller\s*=\s*["\'](\w+)', source_html)
            if not other_controllers or other_controllers == [c.name]:
                content = (
                    f"<!-- Angular template for {class_name} — migrated from AngularJS -->\n"
                    + migrate_template(source_html)
                )
                return content, "full_file_migrated"

        if raw_template:
            content = (
                f"<!-- Angular template for {class_name} (built from detected patterns) -->\n"
                + migrate_template_from_raw(raw_template)
            )
            return content, "raw_template_fallback"

        content = (
            f"<!-- Angular template for {class_name} -->\n"
            f"<!-- TODO: no AngularJS template found — migrate manually -->\n"
            f"<!-- Common patterns: ng-repeat → *ngFor | ng-if → *ngIf | ng-model → [(ngModel)] -->\n"
            f"<h2>{class_name}</h2>\n"
        )
        return content, "stub"

    def _emit_component(self, c, changes: list, source_html, raw_template) -> None:
        base       = c.name.replace("Controller", "").replace("Ctrl", "").lower()
        class_name = c.name.replace("Controller", "").replace("Ctrl", "") + "Component"
        selector   = f"app-{base}"
        ts_path    = self.out_dir / f"{base}.component.ts"
        html_path  = self.out_dir / f"{base}.component.html"

        # ── DI tokens from the IR Class node ─────────────────────────────
        di_tokens: list[str] = getattr(c, "di", [])

        if di_tokens:
            print(f"[ControllerToComponent] DI for {c.name}: {di_tokens}")
        else:
            print(f"[ControllerToComponent] DI for {c.name}: (none detected)")

        # ── TypeScript component ──────────────────────────────────────────
        scope_properties: list[str] = getattr(c, "scope_writes",  []) or []
        scope_methods:    list[dict] = getattr(c, "scope_methods", []) or []
        init_calls_list:  list[str]  = getattr(c, "init_calls",   []) or []

        # Build map of {method_name: [fetch_fn_names]} from http calls
        # so method stubs can call their own fetch methods
        http_calls_by_method: dict[str, list[str]] = {}
        for call in (self._http_calls or []):
            om = getattr(call, "owner_method", None)
            if not om or getattr(call, "owner_controller", None) != c.name:
                continue
            method = getattr(call, "method", "get")
            url    = getattr(call, "url", None)
            if url:
                segments = [s for s in url.strip("/").split("/") if s and s != "api"]
                if segments:
                    clean = [s for s in segments if not s.startswith(":")][-2:]
                    name_part = "".join(w.capitalize() for w in "_".join(clean).replace("-","_").split("_"))
                else:
                    name_part = method.capitalize()
                verb = "fetch" if method == "get" else method.lower()
                fn_name = f"{verb}{name_part}"
            else:
                fn_name = None
            if fn_name:
                http_calls_by_method.setdefault(om, [])
                if fn_name not in http_calls_by_method[om]:
                    http_calls_by_method[om].append(fn_name)

        ts_code = _build_component_ts(
            base, class_name, selector, di_tokens,
            scope_properties=scope_properties,
            scope_methods=scope_methods,
            init_calls=init_calls_list,
            http_calls_by_method=http_calls_by_method,
        )

        if self.dry_run:
            print(f"[DRY RUN] Would write: {ts_path}")
            print(f"[DRY RUN] Preview:\n{ts_code[:400]}")
        else:
            ts_path.parent.mkdir(parents=True, exist_ok=True)
            if not ts_path.exists() or ts_path.read_text(encoding="utf-8") != ts_code:
                ts_path.write_text(ts_code, encoding="utf-8")
                print(f"[ControllerToComponent] Written: {ts_path}")

        changes.append(Change(
            before_id=c.id,
            after_id=f"component_{c.id}",
            source=ChangeSource.RULE,
            reason=f"Controller -> Angular Component written to {ts_path}",
        ))

        # ── HTML template ─────────────────────────────────────────────────
        html_content, method = self._resolve_html_content(c, source_html, raw_template)
        print(f"[ControllerToComponent] Template for {c.name}: method={method}")

        if self.dry_run:
            print(f"[DRY RUN] Would write: {html_path}")
            print(f"[DRY RUN] Preview:\n{html_content[:300]}")
        else:
            if not html_path.exists():
                html_path.write_text(html_content, encoding="utf-8")
                print(f"[ControllerToComponent] Template written: {html_path}")

        changes.append(Change(
            before_id=f"{c.id}_html",
            after_id=f"component_html_{c.id}",
            source=ChangeSource.RULE,
            reason=f"Component template written to {html_path}",
        ))