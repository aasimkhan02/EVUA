from pathlib import Path
from ir.migration_model.change import Change
from ir.migration_model.base import ChangeSource
from pipeline.transformation.angular_project_scaffold import AngularProjectScaffold
from pipeline.transformation.helpers import iter_services
from pipeline.transformation.di_mapper import resolve_di_tokens
from collections import defaultdict




def _sanitize_svc_cb(src):
    if not src:
        return src
    src = src.replace("$scope.", "this.")
    src = src.replace("res.data", "res")
    src = src.replace("response.data", "res")
    return src


def _build_service_ts(
    class_name: str,
    raw_name: str,
    di_tokens: list,
    scope_methods: list = None,
    http_calls_by_method: dict = None,
) -> str:
    """Generate Angular @Injectable from an AngularJS .service() definition.

    scope_methods        -- [{name, params, is_this_method}, ...]  detected by js.py
    http_calls_by_method -- {method_name: [RawHttpCall, ...]}
    """
    scope_methods        = scope_methods        or []
    http_calls_by_method = http_calls_by_method or {}

    resolution = resolve_di_tokens(di_tokens)
    imports_by_module = defaultdict(list)
    imports_by_module["@angular/core"].append("Injectable")

    needs_catch = any(
        getattr(c, "has_catch", False)
        for calls in http_calls_by_method.values() for c in calls
    )
    needs_map = any(
        (not getattr(c, "has_catch", False) and getattr(c, "then_body_src", None))
        for calls in http_calls_by_method.values() for c in calls
    )
    if needs_catch:
        imports_by_module["rxjs"].append("throwError")
        imports_by_module["rxjs/operators"].append("catchError")
    if needs_map:
        imports_by_module["rxjs/operators"].append("map")

    for symbol, module in resolution.imports:
        if symbol not in imports_by_module[module]:
            imports_by_module[module].append(symbol)

    custom_params = []
    for svc_token in resolution.custom_services:
        svc_class = svc_token
        svc_param = svc_class[0].lower() + svc_class[1:]
        imports_by_module["./" + svc_token.lower() + ".service"].append(svc_class)
        custom_params.append("private " + svc_param + ": " + svc_class)

    def _imp():
        out = []
        ang = sorted(k for k in imports_by_module if k.startswith("@"))
        loc = sorted(k for k in imports_by_module if not k.startswith("@"))
        for mod in ang + loc:
            out.append("import { " + ", ".join(imports_by_module[mod]) + " } from '" + mod + "';")
        return out

    all_params = resolution.constructor_params + custom_params
    if all_params:
        j = ", ".join(all_params)
        if len(j) > 72:
            sep = ",\n    "
            ctor = "  constructor(\n    " + sep.join(all_params) + "\n  ) {}"
        else:
            ctor = "  constructor(" + j + ") {}"
    else:
        ctor = None

    comment_lines = ["  // " + c for c in resolution.comments]

    method_lines: list = []
    seen: set = set()
    for m in scope_methods:
        mname = m["name"]
        if mname in seen:
            continue
        seen.add(mname)
        param_str = ", ".join(p + ": any" for p in m.get("params", []))
        owned = http_calls_by_method.get(mname, [])
        method_lines.append("")
        method_lines.append("  " + mname + "(" + param_str + ") {")
        if owned:
            for call in owned:
                if getattr(call, "uses_q", False):
                    method_lines.append("    // TODO: $q.defer() — migrate to RxJS Observable")
                    continue
                mv       = getattr(call, "method", "get")
                url      = getattr(call, "url", None)
                hc       = getattr(call, "has_catch", False)
                then_src = _sanitize_svc_cb(getattr(call, "then_body_src",    None))
                cth_src  = _sanitize_svc_cb(getattr(call, "catch_body_src",   None))
                req_body = _sanitize_svc_cb(getattr(call, "request_body_src", None))
                if url is None:
                    _url_src = getattr(call, 'url_src', None)
                    if _url_src:
                        import re as _re
                        ue = _re.sub(r"'([^']+)'\s*\+\s*(\w+)", r'`\1${\2}`', _url_src)
                        ue = _re.sub(r'(\w+)\s*\+\s*"([^"]+)"', r'`${\1}\2`', ue)
                        print('[svc DEBUG] dynamic URL: ' + repr(_url_src) + ' -> ' + repr(ue))
                    else:
                        ue = "'/'"
                elif url.startswith("'") or url.startswith('"'):
                    ue = url
                else:
                    ue = "'" + url + "'"
                if mv in ("post", "put", "patch") and req_body:
                    base = "this.http." + mv + "(" + ue + ", " + req_body + ")"
                else:
                    base = "this.http." + mv + "(" + ue + ")"
                if hc:
                    import re as _re
                    method_lines += [
                        "    return " + base,
                        "      .pipe(",
                        "        catchError((err) => {",
                    ]
                    if cth_src:
                        method_lines.append("          // AngularJS .catch() — review and adapt:")
                        method_lines += ["          " + ln for ln in cth_src.splitlines()]
                        # Only add throwError if the catch body does not already end
                        # with a throw or return — otherwise we emit dead/unreachable code.
                        _ends_with_flow = _re.search(
                            r"(^|\n)\s*(throw|return)\b", cth_src.rstrip()
                        )
                        if not _ends_with_flow:
                            method_lines.append("          return throwError(() => err);")
                    else:
                        method_lines.append("          // TODO: port .catch() logic")
                        method_lines.append("          return throwError(() => err);")
                    method_lines += [
                        "        })",
                        "      );",
                    ]
                elif then_src:
                    import re as _re2
                    # Detect identity map: then body is just 'return res' (after
                    # res.data → res sanitisation). Emitting map(res => { return res; })
                    # compiles but adds noise. Strip it — return the Observable directly.
                    _stripped_then = then_src.strip().rstrip(";")
                    _is_identity = _stripped_then in ("return res", "return res.data", "return response")
                    if _is_identity:
                        method_lines.append("    return " + base + ";")
                    else:
                        method_lines += [
                            "    return " + base,
                            "      .pipe(",
                            "        map((res: any) => {",
                            "          // AngularJS .then() — review and adapt:",
                        ]
                        method_lines += ["          " + ln for ln in then_src.splitlines()]
                        method_lines += ["        })", "      );"]
                else:
                    method_lines.append("    return " + base + ";")
        else:
            method_lines.append("    // TODO: migrate from AngularJS this." + mname)
        method_lines.append("  }")

    lines = _imp()
    lines += ["", "@Injectable({", "  providedIn: 'root'", "})",
              "export class " + class_name + " {"]
    if comment_lines:
        lines.extend(comment_lines)
    if ctor:
        lines.append(ctor)
    if method_lines:
        lines.extend(method_lines)
    else:
        lines.append("  // TODO: migrate service logic from AngularJS " + raw_name)
    lines += ["}", ""]
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

            _svc_methods = [m for m in (getattr(node, "scope_methods", []) or [])
                            if m.get("is_this_method")]
            if _svc_methods:
                print(f"[ServiceToInjectable] Methods for {raw_name}: "
                      f"{[m['name'] for m in _svc_methods]}")
            _svc_http: dict = {}
            for _c in (getattr(analysis, "http_calls", []) or []):
                _om = getattr(_c, "owner_method", None)
                if _om and getattr(_c, "owner_controller", None) == raw_name:
                    _svc_http.setdefault(_om, []).append(_c)
            ts_code = _build_service_ts(
                class_name, raw_name, di_tokens,
                scope_methods=_svc_methods,
                http_calls_by_method=_svc_http,
            )

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