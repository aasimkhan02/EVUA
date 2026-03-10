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
    parts = name.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


def _infer_prop_name(url: str | None) -> str:
    if not url:
        return "data"
    segments = [s for s in url.strip("/").split("/") if s and s != "api"]
    clean = [s for s in segments if not s.startswith(":")]
    if not clean:
        return "data"
    last = clean[-1].replace("-", "_")
    parts = last.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


def _sanitize_angularjs_callback(src: str) -> str:
    """
    Rewrite AngularJS callback/body text to valid Angular:
      $scope.x     ->  this.x  (component property)
      res.data     ->  res     (HttpClient returns body directly)
      response.data -> res
    """
    if not src:
        return src
    src = src.replace("$scope.", "this.")
    src = src.replace("res.data", "res")
    src = src.replace("response.data", "res")
    return src


def _js_concat_to_template_literal(url_src: str) -> str:
    """
    Convert a JS string-concat URL expression to a TypeScript template literal.

    Examples:
      "'/api/users/' + id"          → "`/api/users/${id}`"
      "baseUrl + '/items/' + item"  → "`${baseUrl}/items/${item}`"
      "'/api/search'"               → "'/api/search'"   (plain string, unchanged)
    """
    import re as _re

    # Strip outer whitespace
    expr = url_src.strip()

    # If it's already a plain string literal, just return it quoted
    if (_re.fullmatch(r"'[^']*'", expr) or _re.fullmatch(r'"[^"]*"', expr)):
        return expr

    # Split on ' + ' boundaries
    parts = [p.strip() for p in _re.split(r"\s*\+\s*", expr)]

    result = ""
    for part in parts:
        # String literal part — strip quotes and append raw text
        m_lit = _re.fullmatch(r"['\"](.*)['\"](.*)", part, _re.DOTALL)
        if m_lit:
            result += m_lit.group(1)
        elif _re.fullmatch(r"'[^']*'", part):
            result += part[1:-1]
        elif _re.fullmatch(r'"[^"]*"', part):
            result += part[1:-1]
        else:
            # Variable / expression — wrap in ${}
            result += "${" + part + "}"

    return f"`{result}`"


def _build_inline_http_call(call, known_props: set | None = None) -> list[str]:
    """
    Render a single RawHttpCall as inline TypeScript statements suitable
    for inclusion directly inside an existing method body.

    Returns a list of lines (indented with 4 spaces to sit inside a method).

    Possible shapes:

    Simple GET (no then/catch source):
        this.http.get('/api/users').subscribe((res: any) => {
          this.users = res;
        });

    With then_body_src (migrated success callback):
        this.http.get('/api/users').subscribe((res: any) => {
          // AngularJS .then() — review and adapt:
          <then_body_src lines>
        });

    With catch:
        this.http.get('/api/users')
          .pipe(catchError((err) => {
            // AngularJS .catch() — review and adapt:
            <catch_body_src lines, or TODO>
            return throwError(() => err);
          }))
          .subscribe((res: any) => { ... });

    POST/PUT/PATCH with request body:
        this.http.post('/api/users', <request_body_src>).subscribe(...);
    """
    method   = getattr(call, "method", "get")
    url      = getattr(call, "url", None)
    has_catch   = getattr(call, "has_catch", False)
    then_src    = _sanitize_angularjs_callback(getattr(call, "then_body_src", None))
    catch_src   = _sanitize_angularjs_callback(getattr(call, "catch_body_src", None))
    req_body    = _sanitize_angularjs_callback(getattr(call, "request_body_src", None))

    # url_src is set by js.py for dynamic URLs (e.g. "'/api/users/' + id").
    # When present, convert to a TypeScript template literal.
    url_src = getattr(call, "url_src", None)

    if url:
        url_lit = f"'{url}'"
    elif url_src:
        url_lit = _js_concat_to_template_literal(url_src)
    else:
        url_lit = "'/'"  # unknown dynamic URL
        url_lit += "'"
    prop    = _infer_prop_name(url)
    # Guard: if the inferred prop name is not a known class property,
    # set prop to None — the subscribe body will emit a TODO comment instead
    # of assigning to an undeclared property (which fails with strict:true).
    if known_props is not None and prop not in known_props:
        prop = None

    # Build the http call expression (first line portion)
    if method in ("post", "put", "patch") and req_body:
        http_expr = f"this.http.{method}({url_lit}, {req_body})"
    else:
        http_expr = f"this.http.{method}({url_lit})"

    # Build subscribe callback body
    if then_src:
        # Indent the original then body and wrap in a comment
        then_lines = then_src.splitlines()
        sub_body = ["      // AngularJS .then() — review and adapt:"]
        sub_body += [f"      {ln}" for ln in then_lines]
    elif prop is not None:
        sub_body = [f"      this.{prop} = res;"]
    else:
        sub_body = ["      // TODO: assign response — add a typed property to this class"]

    # Build catch pipe if needed
    if has_catch:
        catch_lines: list[str] = []
        if catch_src:
            catch_lines.append("          // AngularJS .catch() — review and adapt:")
            for ln in catch_src.splitlines():
                catch_lines.append(f"          {ln}")
        else:
            catch_lines.append("          // TODO: port AngularJS .catch() logic")
        # Only append throwError if catch_src does not already end with throw/return
        _ends_with_flow = (
            catch_src and re.search(r"(^|\n)\s*(throw|return)\b", catch_src.rstrip())
        )
        if not _ends_with_flow:
            catch_lines.append("          return throwError(() => err);")

        lines = [
            f"    {http_expr}",
            f"      .pipe(",
            f"        catchError((err) => {{",
        ]
        lines += catch_lines
        lines += [
            f"        }})",
            f"      )",
            f"      .subscribe((res: any) => {{",
        ]
        lines += sub_body
        lines.append("      });")
    else:
        lines = [f"    {http_expr}.subscribe((res: any) => {{"]
        lines += sub_body
        lines.append("    });")

    return lines


def _build_component_ts(
    base: str,
    class_name: str,
    selector: str,
    di_tokens: list[str],
    scope_properties: list[str] | None = None,
    scope_methods: list[dict] | None = None,
    init_calls: list[str] | None = None,
    # NEW: map of method_name → [RawHttpCall, ...] (full objects, not just names)
    http_calls_by_method: dict[str, list] | None = None,
    # NEW: set of method names that own at least one http call with has_catch=True
    methods_needing_catch_imports: set[str] | None = None,
) -> str:
    resolution = resolve_di_tokens(di_tokens)
    scope_properties    = scope_properties    or []
    scope_methods       = scope_methods       or []
    init_calls          = init_calls          or []
    http_calls_by_method = http_calls_by_method or {}
    methods_needing_catch_imports = methods_needing_catch_imports or set()

    # Determine whether any method needs catchError/throwError imports
    needs_catch_imports = bool(methods_needing_catch_imports)

    # ── Collect imports ───────────────────────────────────────────────────
    from collections import defaultdict
    imports_by_module: dict[str, list[str]] = defaultdict(list)
    needs_oninit = bool(init_calls)
    imports_by_module["@angular/core"].append("Component")
    if needs_oninit:
        imports_by_module["@angular/core"].append("OnInit")

    # HttpClient import only needed if there are any http calls
    any_http = any(
        calls for calls in http_calls_by_method.values()
        if any(not getattr(c, "uses_q", False) for c in calls)
    )
    if any_http:
        imports_by_module["@angular/common/http"].append("HttpClient")

    if needs_catch_imports:
        imports_by_module["rxjs/operators"].append("catchError")
        imports_by_module["rxjs"].append("throwError")

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

    # ── Constructor ───────────────────────────────────────────────────────
    # Add HttpClient to constructor if needed
    ctor_params = list(resolution.constructor_params)
    if any_http:
        ctor_params = [p for p in ctor_params if "HttpClient" not in p]
        ctor_params.insert(0, "private http: HttpClient")
    all_params = ctor_params + custom_params

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

    method_names = {m["name"] for m in scope_methods}
    seen_props: set[str] = set()
    prop_lines: list[str] = []
    for pname in scope_properties:
        if pname.startswith("$") or pname in method_names or pname in seen_props:
            continue
        seen_props.add(pname)
        prop_lines.append(f"  {pname}!: any;  // TODO: add proper type")

    # ── Class methods — HTTP calls inlined directly ───────────────────────
    method_lines: list[str] = []
    seen_methods: set[str] = set()

    for m in scope_methods:
        mname = m["name"]
        if mname.startswith("$") or mname in seen_methods:
            continue
        seen_methods.add(mname)
        params = ", ".join(f"{p}: any" for p in m["params"])
        method_lines.append(f"\n  {mname}({params}): void {{")

        owned_calls = http_calls_by_method.get(mname, [])
        if owned_calls:
            for call in owned_calls:
                if getattr(call, "uses_q", False):
                    method_lines.append("    // TODO: $q.defer()/$q.all() — migrate to RxJS Observable")
                else:
                    method_lines.extend(_build_inline_http_call(call, known_props=set(scope_properties)))
        else:
            method_lines.append(f"    // TODO: migrate from $scope.{mname}")

        method_lines.append("  }")

    # ── ngOnInit ──────────────────────────────────────────────────────────
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

        raw_templates = getattr(analysis, "raw_templates", []) or []

        template_html_by_controller: dict[str, str] = {}
        for t in raw_templates:
            ctrl     = getattr(t, "controller", None)
            raw_html = getattr(t, "raw_html", "") or ""
            if ctrl and raw_html.strip():
                template_html_by_controller[ctrl] = raw_html

        for t in raw_templates:
            raw_html = getattr(t, "raw_html", "") or ""
            if not raw_html.strip():
                continue
            for ctrl_match in re.finditer(r'\bng-controller\s*=\s*["\'](\w+)', raw_html):
                ctrl_name = ctrl_match.group(1)
                if ctrl_name not in template_html_by_controller:
                    template_html_by_controller[ctrl_name] = raw_html

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

        di_tokens: list[str] = getattr(c, "di", [])

        if di_tokens:
            print(f"[ControllerToComponent] DI for {c.name}: {di_tokens}")
        else:
            print(f"[ControllerToComponent] DI for {c.name}: (none detected)")

        scope_properties: list[str] = getattr(c, "scope_writes",  []) or []
        scope_methods:    list[dict] = getattr(c, "scope_methods", []) or []
        init_calls_list:  list[str]  = getattr(c, "init_calls",   []) or []

        # Build map of {method_name: [RawHttpCall, ...]} — full call objects
        # so _build_component_ts can inline them directly.
        http_calls_by_method: dict[str, list] = {}
        methods_needing_catch_imports: set[str] = set()

        for call in (self._http_calls or []):
            om = getattr(call, "owner_method", None)
            if not om or getattr(call, "owner_controller", None) != c.name:
                continue
            http_calls_by_method.setdefault(om, []).append(call)
            if getattr(call, "has_catch", False):
                methods_needing_catch_imports.add(om)

        ts_code = _build_component_ts(
            base, class_name, selector, di_tokens,
            scope_properties=scope_properties,
            scope_methods=scope_methods,
            init_calls=init_calls_list,
            http_calls_by_method=http_calls_by_method,
            methods_needing_catch_imports=methods_needing_catch_imports,
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