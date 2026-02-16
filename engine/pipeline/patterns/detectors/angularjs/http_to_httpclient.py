from pathlib import Path
from ir.migration_model.change import Change
from ir.migration_model.base import ChangeSource
from pipeline.patterns.roles import SemanticRole
from pipeline.transformation.angular_project_scaffold import AngularProjectScaffold

HTTP_CLIENT_IMPORT = "import { HttpClient } from '@angular/common/http';\n"
HTTP_CLIENT_MODULE_IMPORT = "import { HttpClientModule } from '@angular/common/http';\n"


class HttpToHttpClientRule:
    def __init__(self, out_dir="out/angular-app"):
        self.project = AngularProjectScaffold(out_dir)
        self.app_dir = Path(out_dir) / "src" / "app"

    def _ensure_httpclient_module(self):
        app_module = self.app_dir / "app.module.ts"
        if not app_module.exists():
            return

        text = app_module.read_text(encoding="utf-8")

        if "HttpClientModule" not in text:
            if HTTP_CLIENT_MODULE_IMPORT not in text:
                text = HTTP_CLIENT_MODULE_IMPORT + text

            text = text.replace(
                "imports: [BrowserModule, AppRoutingModule]",
                "imports: [BrowserModule, AppRoutingModule, HttpClientModule]",
            )

            app_module.write_text(text, encoding="utf-8")

    def _ensure_httpclient_in_component(self, component_ts: Path):
        if not component_ts.exists():
            return

        text = component_ts.read_text(encoding="utf-8")

        if "HttpClient" not in text:
            if HTTP_CLIENT_IMPORT not in text:
                text = HTTP_CLIENT_IMPORT + text

            # naive constructor injection
            if "constructor(" in text:
                text = text.replace("constructor(", "constructor(private http: HttpClient, ")
            else:
                text = text.replace(
                    "export class",
                    "export class",
                )

            component_ts.write_text(text, encoding="utf-8")

    def _rewrite_http_calls(self, component_ts: Path):
        text = component_ts.read_text(encoding="utf-8")

        text = text.replace("$http.get(", "this.http.get(")
        text = text.replace("$http.post(", "this.http.post(")
        text = text.replace("$http.put(", "this.http.put(")
        text = text.replace("$http.delete(", "this.http.delete(")

        text = text.replace(".then(", ".subscribe(")

        component_ts.write_text(text, encoding="utf-8")

    def apply(self, analysis, patterns):
        changes = []
        self.project.ensure()
        self._ensure_httpclient_module()

        for call, role, _conf in patterns.matched_patterns:
            if role != SemanticRole.HTTP_CALL:
                continue

            # Heuristic: map controller name → component file
            name = call.file.split("\\")[-1].replace(".js", "").replace(".controller", "")
            component_ts = self.app_dir / f"{name}.component.ts"

            if component_ts.exists():
                self._ensure_httpclient_in_component(component_ts)
                self._rewrite_http_calls(component_ts)

            changes.append(
                Change(
                    before_id=f"http_{call.file}_{call.method}",
                    after_id=f"httpclient_{call.file}_{call.method}",
                    source=ChangeSource.RULE,
                    reason=f"$http.{call.method} → HttpClient.{call.method}() + subscribe() rewrite",
                )
            )

        return changes
