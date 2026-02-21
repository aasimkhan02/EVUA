print("HttpToHttpClientRule LOADED")

from pathlib import Path
from ir.migration_model.change import Change
from ir.migration_model.base import ChangeSource
from pipeline.transformation.angular_project_scaffold import AngularProjectScaffold
from pipeline.transformation.helpers import iter_http_calls

HTTP_CLIENT_IMPORT        = "import { HttpClient } from '@angular/common/http';\n"
HTTP_CLIENT_MODULE_IMPORT = "import { HttpClientModule } from '@angular/common/http';\n"


def _owner_to_component_base(call) -> str:
    """
    Derive the Angular component base name from the HTTP call's owner.

    Priority:
      1. call.owner_controller — e.g. "UserController" -> "user"
                                      "AuthService"     -> "auth"
      2. call.file stem        — fallback for unowned calls
    """
    owner = getattr(call, "owner_controller", None)
    if owner:
        return (
            owner
            .replace("Controller", "")
            .replace("Ctrl", "")
            .replace("Service", "")
            .replace("Svc", "")
            .replace("Factory", "")
            .lower()
            .strip("_")
        )
    file_attr = getattr(call, "file", None) or getattr(call, "source_file", "unknown")
    return Path(file_attr).stem.replace(".controller", "").lower()


class HttpToHttpClientRule:
    def __init__(self, out_dir="out/angular-app"):
        self.project = AngularProjectScaffold(out_dir)
        self.app_dir = Path(out_dir) / "src" / "app"

    def apply(self, analysis, patterns):
        print("\n========== HttpToHttpClientRule.apply() ==========")
        changes = []
        self.project.ensure()
        self._ensure_httpclient_module()

        calls = list(iter_http_calls(analysis, patterns))
        print(f"[HttpToHttpClient] HTTP calls detected: {len(calls)}")

        if not calls:
            print("[HttpToHttpClient] No HTTP calls matched. "
                  "Check SemanticRole.HTTP_CALL in patterns or analysis.http_calls.")

        for call in calls:
            self._migrate_call(call, changes)

        print("========== HttpToHttpClientRule DONE ==========\n")
        return changes

    # ------------------------------------------------------------------
    # AppModule patching
    # ------------------------------------------------------------------

    def _ensure_httpclient_module(self):
        app_module = self.app_dir / "app.module.ts"
        if not app_module.exists():
            print("[HttpToHttpClient] app.module.ts missing — run scaffold first")
            return

        text = app_module.read_text(encoding="utf-8")
        if "HttpClientModule" in text:
            return  # already patched — write nothing

        if HTTP_CLIENT_MODULE_IMPORT not in text:
            text = HTTP_CLIENT_MODULE_IMPORT + text
        text = text.replace(
            "imports: [BrowserModule, AppRoutingModule]",
            "imports: [BrowserModule, AppRoutingModule, HttpClientModule]",
        )
        app_module.write_text(text, encoding="utf-8")
        print("[HttpToHttpClient] HttpClientModule added to AppModule")

    # ------------------------------------------------------------------
    # Per-call migration
    # ------------------------------------------------------------------

    def _migrate_call(self, call, changes: list):
        method    = getattr(call, "method", "get")
        url       = getattr(call, "url", None)
        file_attr = getattr(call, "file", None) or getattr(call, "source_file", "unknown")
        owner     = getattr(call, "owner_controller", None)

        base       = _owner_to_component_base(call)
        selector   = f"app-{base}"
        class_name = base.capitalize() + "Component"
        comp_ts    = self.app_dir / f"{base}.component.ts"

        print(f"[HttpToHttpClient] Migrating: {owner or file_attr} -> {method} {url} -> {comp_ts.name}")

        self._ensure_component_base(comp_ts, selector, class_name)

        is_q_defer = method.startswith("q_")

        if method in ("get", "post", "put", "delete", "patch"):
            self._append_http_method(comp_ts, method, url)
        elif is_q_defer:
            self._append_q_defer_stub(comp_ts)

        call_id = getattr(call, "id", f"http_{file_attr}_{method}")

        # q_defer reason string is read by WatcherRiskRule to force MANUAL
        if is_q_defer:
            reason = (
                f"$q.{method}() detected in {owner or file_attr} — "
                f"q_defer stub written to {comp_ts} (MANUAL review required)"
            )
        else:
            reason = (
                f"$http.{method}({url}) -> HttpClient.{method}() "
                f"migrated into {comp_ts}"
            )

        changes.append(Change(
            before_id=call_id,
            after_id=f"httpclient_{base}_{method}",
            source=ChangeSource.RULE,
            reason=reason,
        ))

    # ------------------------------------------------------------------
    # Component file helpers
    # ------------------------------------------------------------------

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

    def _append_http_method(self, comp_ts: Path, method: str, url):
        if not comp_ts.exists():
            self._ensure_component_base(comp_ts, "app-unknown", "UnknownComponent")

        text = comp_ts.read_text(encoding="utf-8")
        if HTTP_CLIENT_IMPORT not in text:
            text = HTTP_CLIENT_IMPORT + text

        # Unique fn name per URL so multiple GET calls don't collide
        # e.g. load_get_api_users, load_get_api_products
        if url:
            slug    = url.strip("/").replace("/", "_").replace("-", "_")
            fn_name = f"load_{method}_{slug}"
        else:
            fn_name = f"load_{method}"

        if fn_name in text:
            return  # idempotent

        url_literal = f"'{url}'" if url else "'/'"
        method_code = (
            f"\n  {fn_name}() {{\n"
            f"    this.http.{method}({url_literal}).subscribe((res: any) => {{\n"
            f"      this.data = res;\n"
            f"    }});\n"
            f"  }}\n"
        )
        comp_ts.write_text(self._inject_into_class(text, method_code), encoding="utf-8")

    def _append_q_defer_stub(self, comp_ts: Path):
        if not comp_ts.exists():
            self._ensure_component_base(comp_ts, "app-unknown", "UnknownComponent")

        text = comp_ts.read_text(encoding="utf-8")
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
        comp_ts.write_text(self._inject_into_class(text, method_code), encoding="utf-8")