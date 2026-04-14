"""
AppModuleUpdaterRule
====================
Rewrites src/app/app.module.ts after all other rules have run,
declaring every generated component, service, pipe, and guard.

Run ORDER: must be LAST in the rule list (after controllers, services,
           http, routing — so all .component.ts / .service.ts files exist).

What it does
------------
1. Scans the output src/app/ directory for generated *.component.ts,
   *.service.ts, and *.pipe.ts files.
2. Collects guard files (*.guard.ts) for the providers[] array.
3. Collects resolver files (*.resolver.ts) for providers[].
4. Rewrites app.module.ts with:
     declarations: [AppComponent, ...Components, ...Pipes]
     imports:      [BrowserModule, AppRoutingModule, HttpClientModule, FormsModule?]
     providers:    [...Services, ...Guards, ...Resolvers]
     bootstrap:    [AppComponent]

Design decisions
----------------
- FormsModule is added if any component template contains [(ngModel)].
- HttpClientModule is added if any *.service.ts or *.component.ts
  imports HttpClient (always safe to include — it's idempotent).
- Existing app.module.ts is fully replaced (not patched) — it was a
  scaffold stub anyway.
- Pipe and guard detection is file-name-based (no AST needed):
    *.component.ts  → declarations[]
    *.pipe.ts       → declarations[]
    *.guard.ts      → providers[]
    *.resolver.ts   → providers[]
    *.service.ts    → providers[]  (except AppModule itself)
"""

from pathlib import Path
from typing import Optional
import re

from ir.migration_model.change import Change
from ir.migration_model.base import ChangeSource
from pipeline.transformation.angular_project_scaffold import AngularProjectScaffold

# Built-in Angular pipes that may be needed based on template usage
_BUILTIN_PIPE_IMPORTS = {
    "DatePipe":      "@angular/common",
    "CurrencyPipe":  "@angular/common",
    "DecimalPipe":   "@angular/common",
    "UpperCasePipe": "@angular/common",
    "LowerCasePipe": "@angular/common",
    "PercentPipe":   "@angular/common",
    "JsonPipe":      "@angular/common",
    "SlicePipe":     "@angular/common",
    "AsyncPipe":     "@angular/common",
    "KeyValuePipe":  "@angular/common",
    "TitleCasePipe": "@angular/common",
}


def _class_name_from_file(stem: str, suffix: str) -> str:
    """
    'user-detail.component' → 'UserDetailComponent'
    'auth.guard'             → 'AuthGuard'
    'prefs.resolver'         → 'PrefsResolver'
    'user.service'           → 'UserService'  (but lowercase in file)
    """
    # stem already has suffix stripped by caller — just PascalCase the base
    parts = re.split(r'[-_]', stem)
    return "".join(p.capitalize() for p in parts) + suffix


def _to_pascal(stem: str) -> str:
    """'user-detail' → 'UserDetail'"""
    return "".join(p.capitalize() for p in re.split(r'[-_.]', stem))


def _extract_class_name(content: str) -> Optional[str]:
    """
    Extract the exported class name from TypeScript file content.
    Matches: export class ProductCardComponent {
    Returns the class name string, or None if not found.
    """
    m = re.search(r'\bexport\s+class\s+(\w+)', content)
    return m.group(1) if m else None


def _scan_app_dir(app_dir: Path) -> dict:
    """
    Walk app_dir and collect all generated files by category.
    Returns {
        'components': [(ClassName, filename_no_ext), ...],
        'pipes':      [...],
        'guards':     [...],
        'resolvers':  [...],
        'services':   [...],
        'has_ngmodel': bool,
        'has_httpclient': bool,
    }
    """
    components: list[tuple[str, str]] = []
    pipes:      list[tuple[str, str]] = []
    guards:     list[tuple[str, str]] = []
    resolvers:  list[tuple[str, str]] = []
    services:   list[tuple[str, str, str]] = []
    has_ngmodel    = False
    has_httpclient = False

    SKIP_FILES = {"app.component.ts", "app.module.ts"}

    # Scan HTML templates for [(ngModel)] and built-in pipe usage
    builtin_pipes_used: set = set()
    for html_file in sorted(app_dir.glob("*.component.html")):
        try:
            html_content = html_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            html_content = ""
        if "[(ngModel)]" in html_content or "ngModel" in html_content:
            has_ngmodel = True
        # Detect built-in Angular pipe usage: "| date", "| currency", etc.
        for pipe_re, pipe_class in [
            (r'\|\s*date\b',       "DatePipe"),
            (r'\|\s*currency\b',   "CurrencyPipe"),
            (r'\|\s*number\b',     "DecimalPipe"),
            (r'\|\s*uppercase\b',  "UpperCasePipe"),
            (r'\|\s*lowercase\b',  "LowerCasePipe"),
            (r'\|\s*percent\b',    "PercentPipe"),
            (r'\|\s*json\b',       "JsonPipe"),
            (r'\|\s*slice\b',      "SlicePipe"),
            (r'\|\s*async\b',      "AsyncPipe"),
            (r'\|\s*keyvalue\b',   "KeyValuePipe"),
            (r'\|\s*titlecase\b',  "TitleCasePipe"),
        ]:
            if re.search(pipe_re, html_content, re.IGNORECASE):
                builtin_pipes_used.add(pipe_class)

    for ts_file in sorted(app_dir.glob("*.ts")):
        fname = ts_file.name
        if fname in SKIP_FILES:
            continue

        stem = ts_file.stem  # e.g. 'userdetail.component'

        content = ""
        try:
            content = ts_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            pass

        if "ngModel" in content or "[(ngModel)]" in content:
            has_ngmodel = True
        if "HttpClient" in content:
            has_httpclient = True

        if stem.endswith(".component"):
            cls = _extract_class_name(content) or (_to_pascal(stem[:-len(".component")]) + "Component")
            components.append((cls, stem))

        elif stem.endswith(".directive"):
            cls = _extract_class_name(content) or (_to_pascal(stem[:-len(".directive")]) + "Directive")
            components.append((cls, stem))  # @Directive goes in declarations[]

        elif stem.endswith(".pipe"):
            cls = _extract_class_name(content) or (_to_pascal(stem[:-len(".pipe")]) + "Pipe")
            pipes.append((cls, stem))

        elif stem.endswith(".guard"):
            cls = _extract_class_name(content) or (_to_pascal(stem[:-len(".guard")]) + "Guard")
            guards.append((cls, stem))

        elif stem.endswith(".resolver"):
            cls = _extract_class_name(content) or (_to_pascal(stem[:-len(".resolver")]) + "Resolver")
            resolvers.append((cls, stem))

        elif stem.endswith(".service"):
            cls = _extract_class_name(content) or (_to_pascal(stem[:-len(".service")]) + "Service")
            services.append((cls, stem, fname))

    # ── Deduplicate services by class name ───────────────────────────────
    # HttpToHttpClientRule emits e.g. stats.service.ts (class StatsService)
    # ServiceToInjectableRule emits statsservice.service.ts (class StatsService)
    # Both share the same class name → duplicate identifier in app.module.ts.
    # Resolution: among duplicates, prefer the file whose stem matches the
    # pattern <name>service.service (i.e. the ServiceToInjectableRule output),
    # because it contains the full migrated service body. The HttpToHttpClientRule
    # stub is a thin shim that is only needed when there is NO corresponding
    # AngularJS service — if a *service.service.ts already covers it, drop the stub.
    _seen_svc_class: dict[str, tuple[str, str, str]] = {}
    for entry in services:
        cls, stem, fname = entry
        if cls not in _seen_svc_class:
            _seen_svc_class[cls] = entry
        else:
            existing_stem = _seen_svc_class[cls][1]
            # Prefer the file whose stem ends with "service.service" (ServiceToInjectableRule)
            # over a plain "*.service" stub (HttpToHttpClientRule).
            if stem.endswith("service.service"):
                _seen_svc_class[cls] = entry
            # else keep existing
    services = list(_seen_svc_class.values())

    return {
        "components":       components,
        "pipes":            pipes,
        "guards":           guards,
        "resolvers":        resolvers,
        "services":         services,
        "has_ngmodel":      has_ngmodel,
        "has_httpclient":   has_httpclient,
        "_app_dir":         app_dir,
        "builtin_pipes":    builtin_pipes_used,  # DatePipe, CurrencyPipe, etc.
    }


def _build_app_module(scanned: dict) -> str:
    """
    Render the complete app.module.ts string from scanned data.
    """
    components = scanned["components"]
    pipes      = scanned["pipes"]
    guards     = scanned["guards"]
    resolvers  = scanned["resolvers"]
    services   = scanned["services"]

    # ── Import lines ─────────────────────────────────────────────────────
    import_lines: list[str] = [
        "import { NgModule } from '@angular/core';",
        "import { BrowserModule } from '@angular/platform-browser';",
    ]

    if scanned["has_httpclient"]:
        import_lines.append("import { HttpClientModule } from '@angular/common/http';")

    if scanned["has_ngmodel"]:
        import_lines.append("import { FormsModule } from '@angular/forms';")

    import_lines += [
        "import { AppComponent } from './app.component';",
        "import { AppRoutingModule } from './app-routing.module';",
    ]

    for cls, stem in components:
        import_lines.append(f"import {{ {cls} }} from './{stem}';")

    for cls, stem in pipes:
        import_lines.append(f"import {{ {cls} }} from './{stem}';")

    # ── Built-in Angular pipes needed by templates ───────────────────────
    # MUST be computed BEFORE the import loop that references builtin_pipe_entries
    builtin_pipes = scanned.get("builtin_pipes", set())
    builtin_pipe_entries: list[tuple[str, str]] = []
    for pipe_class in sorted(builtin_pipes):
        mod = _BUILTIN_PIPE_IMPORTS.get(pipe_class, "@angular/common")
        builtin_pipe_entries.append((pipe_class, mod))
    print(f"[AppModuleUpdater] Built-in pipes detected in templates: {[p for p,_ in builtin_pipe_entries]}")

    # Built-in Angular pipes — imported from @angular/common
    _seen_bp_modules: dict = {}
    for pipe_class, mod in builtin_pipe_entries:
        _seen_bp_modules.setdefault(mod, []).append(pipe_class)
    for mod, classes in sorted(_seen_bp_modules.items()):
        import_lines.append(f"import {{ {', '.join(classes)} }} from '{mod}';")

    for cls, stem in guards:
        import_lines.append(f"import {{ {cls} }} from './{stem}';")

    for cls, stem in resolvers:
        import_lines.append(f"import {{ {cls} }} from './{stem}';")

    for cls, stem, _fname in services:
        # Skip import if the service file has no @Injectable (e.g. app-init.service.ts)
        # — importing a non-existent class name causes TS2305
        svc_file_check = (scanned.get("_app_dir") or Path(".")) / f"{stem}.ts"
        try:
            _svc_check_content = svc_file_check.read_text(encoding="utf-8", errors="replace")
            if "@Injectable" not in _svc_check_content:
                print(f"[AppModuleUpdater] {stem}.ts: skipping import — no @Injectable (TS2305 prevention)")
                continue
        except Exception:
            pass
        import_lines.append(f"import {{ {cls} }} from './{stem}';")

    # ── declarations[] ────────────────────────────────────────────────────
    decl_items = ["AppComponent"]
    decl_items += [cls for cls, _ in components]
    decl_items += [cls for cls, _ in pipes]
    # NOTE: builtin_pipe_entries (SlicePipe, DatePipe, etc.) must NOT go in declarations[].
    # They are Angular built-ins available via BrowserModule/CommonModule. Declaring them causes NG6001.

    # ── imports[] ────────────────────────────────────────────────────────
    import_mod_items = ["BrowserModule", "AppRoutingModule"]
    if scanned["has_httpclient"]:
        import_mod_items.append("HttpClientModule")
    if scanned["has_ngmodel"]:
        import_mod_items.append("FormsModule")

    # ── providers[] ──────────────────────────────────────────────────────
    # Services that declare @Injectable({providedIn: 'root'}) are globally
    # available without listing them in providers[]. Listing them there too
    # causes a double-registration (harmless but wrong and clutters the module).
    # We check each service file: only add to providers[] if it does NOT use
    # providedIn:'root'.
    provider_items: list[str] = []
    for cls, stem, _fname in services:
        svc_file = (scanned.get("_app_dir") or Path(".")) / f"{stem}.ts"
        try:
            svc_content = svc_file.read_text(encoding="utf-8", errors="replace")
            # Skip from providers[] if:
            # (a) already self-providing via @Injectable({providedIn:'root'})
            # (b) not an @Injectable at all (e.g. app-init.service.ts is a plain function)
            if "providedIn" in svc_content:
                print(f"[AppModuleUpdater] {stem}.ts: skipping providers[] — has providedIn")
                continue
            if "@Injectable" not in svc_content:
                print(f"[AppModuleUpdater] {stem}.ts: skipping providers[] — no @Injectable")
                continue
        except Exception:
            pass
        provider_items.append(cls)
    provider_items += [cls for cls, _ in guards]
    provider_items += [cls for cls, _ in resolvers]

    def _fmt_array(items: list[str], indent: str = "    ") -> str:
        if not items:
            return "[]"
        if len(items) == 1:
            return f"[{items[0]}]"
        joined = f",\n{indent}".join(items)
        return f"[\n{indent}{joined}\n  ]"

    lines: list[str] = list(import_lines)
    lines += [
        "",
        "@NgModule({",
        f"  declarations: {_fmt_array(decl_items)},",
        f"  imports: {_fmt_array(import_mod_items)},",
        f"  providers: {_fmt_array(provider_items)},",
        "  bootstrap: [AppComponent]",
        "})",
        "export class AppModule {}",
    ]

    return "\n".join(lines) + "\n"


class AppModuleUpdaterRule:
    """
    Post-processing rule: rewrites app.module.ts with all generated
    components, services, pipes, guards, and resolvers declared.

    Must be registered LAST in the rule list in cli.py.
    """

    def __init__(self, out_dir: str = "out/angular-app", dry_run: bool = False):
        self.project  = AngularProjectScaffold(out_dir)
        self.app_dir  = Path(out_dir) / "src" / "app"
        self.mod_path = self.app_dir / "app.module.ts"
        self.dry_run  = dry_run

    def apply(self, analysis, patterns):
        print("\n========== AppModuleUpdaterRule.apply() ==========")
        if self.dry_run:
            print("[AppModuleUpdater] DRY RUN — no files will be written")

        changes = []

        if not self.dry_run and not self.app_dir.exists():
            print("[AppModuleUpdater] app_dir does not exist — skipping")
            print("========== AppModuleUpdaterRule DONE ==========\n")
            return changes

        scanned = _scan_app_dir(self.app_dir)

        n_comp = len(scanned["components"])
        n_svc  = len(scanned["services"])
        n_g    = len(scanned["guards"])
        n_r    = len(scanned["resolvers"])
        n_p    = len(scanned["pipes"])
        print(
            f"[AppModuleUpdater] Found: {n_comp} components, {n_svc} services, "
            f"{n_g} guards, {n_r} resolvers, {n_p} pipes"
        )
        print(f"[AppModuleUpdater] FormsModule needed: {scanned['has_ngmodel']}")
        print(f"[AppModuleUpdater] HttpClientModule needed: {scanned['has_httpclient']}")

        new_content = _build_app_module(scanned)

        if self.dry_run:
            print(f"[DRY RUN] Would write: {self.mod_path}")
            print(f"[DRY RUN] Preview:\n{new_content[:600]}")
        else:
            # Always rewrite — it was a static stub before
            self.mod_path.write_text(new_content, encoding="utf-8")
            print(f"[AppModuleUpdater] Written: {self.mod_path}")

        changes.append(Change(
            before_id="app_module_stub",
            after_id="app_module_updated",
            source=ChangeSource.RULE,
            reason=f"app.module.ts updated with {n_comp} components, {n_svc} services, "
                   f"{n_g} guards, {n_r} resolvers, {n_p} pipes",
        ))

        print("========== AppModuleUpdaterRule DONE ==========\n")
        return changes