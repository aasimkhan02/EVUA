print("HttpToHttpClientRule LOADED")

from pathlib import Path
from ir.migration_model.change import Change
from ir.migration_model.base import ChangeSource
from pipeline.transformation.angular_project_scaffold import AngularProjectScaffold
from pipeline.transformation.helpers import iter_http_calls

HTTP_CLIENT_IMPORT        = "import { HttpClient } from '@angular/common/http';\n"
HTTP_CLIENT_MODULE_IMPORT = "import { HttpClientModule } from '@angular/common/http';\n"


class HttpToHttpClientRule:
    def __init__(self, out_dir="out/angular-app"):
        self.project  = AngularProjectScaffold(out_dir)
        self.app_dir  = Path(out_dir) / "src" / "app"

    def apply(self, analysis, patterns):
        print("\n========== HttpToHttpClientRule.apply() ==========")
        changes = []
        self.project.ensure()
        self._ensure_httpclient_module()

        # HttpCall is NOT an IR type — lives in analysis layer
        # Expected: .id, .file, .method, .url
        calls = list(iter_http_calls(analysis, patterns))
        print(f"[HttpToHttpClient] HTTP calls detected: {len(calls)}")

        if not calls:
            print("[HttpToHttpClient] ⚠️  No HTTP calls matched. "
                  "Check SemanticRole.HTTP_CALL in patterns or analysis.http_calls.")

        for call in calls:
            self._migrate_call(call, changes)

        print("========== HttpToHttpClientRule DONE ==========\n")
        return changes

    # ------------------------------------------------------------------
    # AppModule patching — guard is checked BEFORE any write or log
    # ------------------------------------------------------------------

    def _ensure_httpclient_module(self):
        app_module = self.app_dir / "app.module.ts"
        if not app_module.exists():
            print("[HttpToHttpClient] ⚠️  app.module.ts missing — run scaffold first")
            return

        text = app_module.read_text(encoding="utf-8")

        # Guard first — only proceed if HttpClientModule is actually missing
        if "HttpClientModule" in text:
            return  # already patched — log nothing, write nothing

        if HTTP_CLIENT_MODULE_IMPORT not in text:
            text = HTTP_CLIENT_MODULE_IMPORT + text

        text = text.replace(
            "imports: [BrowserModule, AppRoutingModule]",
            "imports: [BrowserModule, AppRoutingModule, HttpClientModule]",
        )
        app_module.write_text(text, encoding="utf-8")
        # Log AFTER write so the message only appears when a real change occurred
        print("[HttpToHttpClient] ✅ HttpClientModule added to AppModule")

    # ------------------------------------------------------------------
    # Per-call migration
    # ------------------------------------------------------------------

    def _migrate_call(self, call, changes: list):
        # .file may be called .source_file in some analysis implementations
        file_attr = (
            getattr(call, "file", None)
            or getattr(call, "source_file", "unknown")
        )
        method = getattr(call, "method", "get")
        url    = getattr(call, "url", None)

        print(f"[HttpToHttpClient] Migrating: {file_attr} → {method} {url}")

        base       = Path(file_attr).stem.replace(".controller", "")
        selector   = f"app-{base.lower()}"
        class_name = base.capitalize() + "Component"
        comp_ts    = self.app_dir / f"{base.lower()}.component.ts"

        self._ensure_component_base(comp_ts, selector, class_name)

        if method in ("get", "post", "put", "delete", "patch"):
            self._append_http_method(comp_ts, method, url)
        elif method.startswith("q_"):
            self._append_q_defer_stub(comp_ts)

        call_id = getattr(call, "id", f"http_{file_attr}_{method}")
        changes.append(Change(
            before_id=call_id,
            after_id=f"httpclient_{file_attr}_{method}",
            source=ChangeSource.RULE,
            reason=f"$http.{method} → HttpClient.{method}() migrated into {comp_ts}",
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
        print(f"[HttpToHttpClient] ✅ Created component stub: {comp_ts}")

    @staticmethod
    def _inject_into_class(text: str, code: str) -> str:
        idx = text.rfind("}")
        if idx == -1:
            return text + "\n" + code
        return text[:idx] + code + "\n" + text[idx:]

    def _append_http_method(self, comp_ts: Path, method: str, url: str | None):
        if not comp_ts.exists():
            self._ensure_component_base(comp_ts, "app-services", "ServicesComponent")

        text = comp_ts.read_text(encoding="utf-8")

        if HTTP_CLIENT_IMPORT not in text:
            text = HTTP_CLIENT_IMPORT + text

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
            self._ensure_component_base(comp_ts, "app-services", "ServicesComponent")

        text = comp_ts.read_text(encoding="utf-8")
        if "legacyDeferExample" in text:
            return

        method_code = (
            "\n  legacyDeferExample(): Promise<any> {\n"
            "    return new Promise((resolve, _reject) => {\n"
            "      // TODO: migrate $q.defer() logic manually\n"
            "      resolve(null);\n"
            "    });\n"
            "  }\n"
        )
        comp_ts.write_text(self._inject_into_class(text, method_code), encoding="utf-8")