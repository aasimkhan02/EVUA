print("HttpToHttpClientRule LOADED")

from pathlib import Path
from ir.migration_model.change import Change
from ir.migration_model.base import ChangeSource
from pipeline.transformation.angular_project_scaffold import AngularProjectScaffold
from pipeline.transformation.helpers import iter_http_calls

HTTP_CLIENT_IMPORT        = "import { HttpClient } from '@angular/common/http';\n"
HTTP_CLIENT_MODULE_IMPORT = "import { HttpClientModule } from '@angular/common/http';\n"


def _classify_owner(owner: str) -> str:
    if not owner:
        return "component"
    o = owner.lower()
    if o.endswith("service") or o.endswith("svc") or o.endswith("factory"):
        return "service"
    return "component"


def _owner_to_base(owner: str) -> str:
    if not owner:
        return "unknown"
    return (
        owner
        .replace("Controller", "")
        .replace("Ctrl", "")
        .replace("Service", "")
        .replace("Svc", "")
        .replace("Factory", "")
        .lower()
        .strip("_")
    ) or owner.lower()


def _owner_to_file_base(call) -> tuple:
    owner = getattr(call, "owner_controller", None)
    if owner:
        kind = _classify_owner(owner)
        if kind == "service":
            base = owner.lower().replace(" ", "")
        else:
            base = _owner_to_base(owner)
        return base, kind
    file_attr = getattr(call, "file", None) or getattr(call, "source_file", "unknown")
    base = Path(file_attr).stem.replace(".controller", "").lower()
    return base, "component"


class HttpToHttpClientRule:
    def __init__(self, out_dir: str = "out/angular-app", dry_run: bool = False):
        self.project  = AngularProjectScaffold(out_dir)
        self.app_dir  = Path(out_dir) / "src" / "app"
        self.dry_run  = dry_run

    def apply(self, analysis, patterns):
        print("\n========== HttpToHttpClientRule.apply() ==========")
        if self.dry_run:
            print("[HttpToHttpClient] DRY RUN — no files will be written")

        changes = []

        if not self.dry_run:
            self.project.ensure()
            self._ensure_httpclient_module()

        calls = list(iter_http_calls(analysis, patterns))
        print(f"[HttpToHttpClient] HTTP calls detected: {len(calls)}")

        for call in calls:
            self._migrate_call(call, changes)

        print("========== HttpToHttpClientRule DONE ==========\n")
        return changes

    # -----------------------------------------------------------------------
    # AppModule patching
    # -----------------------------------------------------------------------

    def _ensure_httpclient_module(self):
        app_module = self.app_dir / "app.module.ts"
        if not app_module.exists():
            return
        text = app_module.read_text(encoding="utf-8")
        if "HttpClientModule" in text:
            return
        if HTTP_CLIENT_MODULE_IMPORT not in text:
            text = HTTP_CLIENT_MODULE_IMPORT + text
        text = text.replace(
            "imports: [BrowserModule, AppRoutingModule]",
            "imports: [BrowserModule, AppRoutingModule, HttpClientModule]",
        )
        app_module.write_text(text, encoding="utf-8")
        print("[HttpToHttpClient] HttpClientModule added to AppModule")

    # -----------------------------------------------------------------------
    # Per-call migration
    # -----------------------------------------------------------------------

    def _migrate_call(self, call, changes: list):
        method    = getattr(call, "method", "get")
        url       = getattr(call, "url", None)
        file_attr = getattr(call, "file", None) or getattr(call, "source_file", "unknown")
        owner     = getattr(call, "owner_controller", None)

        base, kind = _owner_to_file_base(call)
        is_q_defer = method.startswith("q_")

        if kind == "service":
            target_ts  = self.app_dir / f"{base}.service.ts"
            class_name = "".join(w.capitalize() for w in base.split("_")) + "Service"
            selector   = None
            if not self.dry_run:
                self._ensure_service_base(target_ts, class_name)
        else:
            target_ts  = self.app_dir / f"{base}.component.ts"
            class_name = base.capitalize() + "Component"
            selector   = f"app-{base}"
            if not self.dry_run:
                self._ensure_component_base(target_ts, selector, class_name)

        print(f"[HttpToHttpClient] {'(dry) ' if self.dry_run else ''}Migrating: "
              f"{owner or file_attr} -> {method} {url} -> {target_ts.name}")

        if not self.dry_run:
            if not is_q_defer:
                if method in ("get", "post", "put", "delete", "patch"):
                    self._append_http_method(target_ts, method, url, kind)
            else:
                self._append_q_defer_stub(target_ts)

        call_id = getattr(call, "id", f"http_{file_attr}_{method}")

        if is_q_defer:
            reason = (
                f"$q.{method}() detected in {owner or file_attr} — "
                f"q_defer stub written to {target_ts} (MANUAL review required)"
            )
        else:
            reason = (
                f"$http.{method}({url}) -> HttpClient.{method}() "
                f"migrated into {target_ts}"
            )

        changes.append(Change(
            before_id=call_id,
            after_id=f"httpclient_{base}_{method}",
            source=ChangeSource.RULE,
            reason=reason,
        ))

    # -----------------------------------------------------------------------
    # File creation helpers
    # -----------------------------------------------------------------------

    def _ensure_service_base(self, svc_ts: Path, class_name: str):
        if svc_ts.exists():
            return
        stub = (
            f"import {{ Injectable }} from '@angular/core';\n"
            f"import {{ HttpClient }} from '@angular/common/http';\n\n"
            f"@Injectable({{ providedIn: 'root' }})\n"
            f"export class {class_name} {{\n\n"
            f"  constructor(private http: HttpClient) {{}}\n\n"
            f"}}\n"
        )
        svc_ts.parent.mkdir(parents=True, exist_ok=True)
        svc_ts.write_text(stub, encoding="utf-8")
        print(f"[HttpToHttpClient] Created service stub: {svc_ts}")

    def _ensure_component_base(self, comp_ts: Path, selector: str, class_name: str):
        if comp_ts.exists():
            return
        stub = (
            f"import {{ Component }} from '@angular/core';\n"
            f"import {{ HttpClient }} from '@angular/common/http';\n\n"
            f"@Component({{\n"
            f"  selector: '{selector}',\n"
            f"  template: '<pre>{{{{ data | json }}}}</pre>'\n"
            f"}})\n"
            f"export class {class_name} {{\n"
            f"  data: any;\n\n"
            f"  constructor(private http: HttpClient) {{}}\n"
            f"}}\n"
        )
        comp_ts.parent.mkdir(parents=True, exist_ok=True)
        comp_ts.write_text(stub, encoding="utf-8")
        print(f"[HttpToHttpClient] Created component stub: {comp_ts}")

    @staticmethod
    def _inject_into_class(text: str, code: str) -> str:
        idx = text.rfind("}")
        if idx == -1:
            return text + "\n" + code
        return text[:idx] + code + "\n" + text[idx:]

    def _append_http_method(self, target_ts: Path, method: str, url, kind: str):
        if not target_ts.exists():
            return
        text = target_ts.read_text(encoding="utf-8")
        if HTTP_CLIENT_IMPORT not in text:
            text = HTTP_CLIENT_IMPORT + text

        if url:
            slug    = url.strip("/").replace("/", "_").replace("-", "_")
            fn_name = f"load_{method}_{slug}"
        else:
            fn_name = f"load_{method}"

        if fn_name in text:
            return  # idempotent

        url_literal = f"'{url}'" if url else "'/'"

        if kind == "service":
            method_code = (
                f"\n  {fn_name}() {{\n"
                f"    return this.http.{method}({url_literal});\n"
                f"  }}\n"
            )
        else:
            method_code = (
                f"\n  {fn_name}() {{\n"
                f"    this.http.{method}({url_literal}).subscribe((res: any) => {{\n"
                f"      this.data = res;\n"
                f"    }});\n"
                f"  }}\n"
            )

        target_ts.write_text(self._inject_into_class(text, method_code), encoding="utf-8")

    def _append_q_defer_stub(self, target_ts: Path):
        if not target_ts.exists():
            return
        text = target_ts.read_text(encoding="utf-8")
        if "legacyDeferExample" in text:
            return
        method_code = (
            "\n  // TODO: $q.defer() detected — migrate manually to RxJS Observable\n"
            "  legacyDeferExample(): Promise<any> {\n"
            "    return new Promise((resolve, _reject) => {\n"
            "      // Replace with: return new Observable(observer => { ... })\n"
            "      resolve(null);\n"
            "    });\n"
            "  }\n"
        )
        target_ts.write_text(self._inject_into_class(text, method_code), encoding="utf-8")