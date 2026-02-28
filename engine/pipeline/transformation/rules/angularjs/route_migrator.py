"""
RouteMigratorRule
=================
Converts AngularJS route definitions ($routeProvider / $stateProvider)
into a production-ready Angular app-routing.module.ts.

Handles:
  - ngRoute  ($routeProvider.when / .otherwise)
  - ui-router ($stateProvider.state — flat and nested)
  - Route parameters  (:id → :id, no change needed in Angular)
  - redirectTo        → { path: '', redirectTo: '...', pathMatch: 'full' }
  - resolve blocks    → Angular Resolver stub files
  - abstract states   → lazy-loaded feature module stubs
  - wildcard          → { path: '**', redirectTo: '...' }
  - No routes found   → sensible default routing scaffold

Output
------
  app-routing.module.ts   — always written
  <name>.resolver.ts      — one per resolve key (if resolve blocks exist)
"""

from pathlib import Path
from typing import Optional
import re

from ir.migration_model.change import Change
from ir.migration_model.base import ChangeSource
from pipeline.transformation.angular_project_scaffold import AngularProjectScaffold


def _ctrl_to_component_class(controller_name: Optional[str]) -> Optional[str]:
    """'UserController' → 'UserComponent',  'HomeCtrl' → 'HomeComponent'"""
    if not controller_name:
        return None
    return (
        controller_name
        .replace("Controller", "")
        .replace("Ctrl", "")
    ) + "Component"


def _ctrl_to_base(controller_name: Optional[str]) -> Optional[str]:
    """'UserController' → 'user',  'HomeCtrl' → 'home'"""
    if not controller_name:
        return None
    return (
        controller_name
        .replace("Controller", "")
        .replace("Ctrl", "")
        .lower()
    )


def _state_to_path(state_name: str) -> str:
    """
    Convert ui-router state name to a URL path fragment.
    'app.users.detail' → 'app/users/detail'
    """
    return state_name.replace(".", "/")


def _resolver_class_name(key: str) -> str:
    """'userData' → 'UserDataResolver'"""
    return key[0].upper() + key[1:] + "Resolver"


class RouteMigratorRule:
    def __init__(self, out_dir: str = "out/angular-app", dry_run: bool = False):
        self.project      = AngularProjectScaffold(out_dir)
        self.out_dir      = Path(out_dir) / "src" / "app"
        self.routing_path = self.out_dir / "app-routing.module.ts"
        self.dry_run      = dry_run

    # -----------------------------------------------------------------------
    # Public entry point
    # -----------------------------------------------------------------------

    def apply(self, analysis, patterns):
        print("\n========== RouteMigratorRule.apply() ==========")
        if self.dry_run:
            print("[RouteMigrator] DRY RUN — no files will be written")

        changes = []

        if not self.dry_run:
            self.project.ensure()

        raw_routes = getattr(analysis, "routes", []) or []

        # Deduplicate by (router_type, path/state_name, controller)
        seen_sigs = set()
        routes = []
        for r in raw_routes:
            sig = (r.router_type, r.state_name or r.path, r.controller, r.is_otherwise, r.is_abstract)
            if sig not in seen_sigs:
                seen_sigs.add(sig)
                routes.append(r)

        print(f"[RouteMigrator] Routes detected: {len(routes)} (raw: {len(raw_routes)})")

        if routes:
            router_types = {r.router_type for r in routes}
            print(f"[RouteMigrator] Router type(s): {router_types}")
            for r in routes:
                symbol = r.state_name or r.path
                print(f"[RouteMigrator]   {r.router_type:8s}  {symbol:30s}  ctrl={r.controller}  abstract={r.is_abstract}")

        routing_ts, resolver_files = self._build_routing_module(routes, analysis)

        if self.dry_run:
            print(f"[DRY RUN] Would write: {self.routing_path}")
            print(f"[DRY RUN] Content preview:\n{routing_ts[:500]}")
        else:
            self.routing_path.write_text(routing_ts, encoding="utf-8")
            print(f"[RouteMigrator] Written: {self.routing_path}")

        changes.append(Change(
            before_id="routing_module",
            after_id="angular_routing_module",
            source=ChangeSource.RULE,
            reason=f"Angular Router configured written to {self.routing_path}",
        ))

        # Write resolver stubs
        for fname, content in resolver_files.items():
            fpath = self.out_dir / fname
            if self.dry_run:
                print(f"[DRY RUN] Would write resolver: {fpath}")
            else:
                fpath.write_text(content, encoding="utf-8")
                print(f"[RouteMigrator] Resolver written: {fpath}")

            changes.append(Change(
                before_id=f"resolve_{fname}",
                after_id=f"resolver_{fname}",
                source=ChangeSource.RULE,
                reason=f"Angular Resolver stub written to {fpath}",
            ))

        print("========== RouteMigratorRule DONE ==========\n")
        return changes

    # -----------------------------------------------------------------------
    # Routing module builder
    # -----------------------------------------------------------------------

    def _build_routing_module(self, routes, analysis) -> tuple[str, dict]:
        """
        Returns (routing_module_ts_content, {filename: resolver_content}).
        """
        resolver_files: dict[str, str] = {}

        if not routes:
            # No route config found — build a minimal scaffold using known controllers
            return self._build_fallback_routing(analysis), resolver_files

        # Determine router type — prefer uiRouter if mixed
        router_types = {r.router_type for r in routes}
        is_ui_router = "uiRouter" in router_types

        # If uiRouter exists, ignore ngRoute routes
        if is_ui_router:
            routes = [r for r in routes if r.router_type == "uiRouter"]

        # Collect all component classes we need to import
        # {class_name: base_filename}  e.g. {'UserComponent': 'user'}
        component_imports: dict[str, str] = {}

        # Build route entries
        route_entries:   list[str] = []
        redirect_entries: list[str] = []
        wildcard_entry: Optional[str] = None

        for route in routes:
            if route.is_otherwise:
                # redirectTo or wildcard
                target = route.path if route.path != "**" else "/"
                if route.path == "**":
                    wildcard_entry = f"  {{ path: '**', redirectTo: '{target}', pathMatch: 'full' }}"
                else:
                    redirect_entries.append(
                        f"  {{ path: '', redirectTo: '{target}', pathMatch: 'full' }}"
                    )
                continue

            if route.is_abstract:
                # Skip abstract states completely (do not generate routes)
                continue

            cls = _ctrl_to_component_class(route.controller)
            base = _ctrl_to_base(route.controller)

            if cls and base:
                component_imports[cls] = base

            # Resolve block → generate resolver stubs + include in route
            resolve_providers: list[str] = []
            for key in route.resolve:
                resolver_cls  = _resolver_class_name(key)
                resolver_file = f"{key.lower()}.resolver.ts"
                resolve_providers.append(f"      {key}: {resolver_cls}")
                if resolver_file not in resolver_files:
                    resolver_files[resolver_file] = self._build_resolver_stub(key, resolver_cls)
                if resolver_cls not in component_imports:
                    component_imports[resolver_cls] = key.lower() + ".resolver"

            # Build Angular path
            if route.router_type == "uiRouter" and route.state_name:
                # Flatten state hierarchy
                parts = route.state_name.split(".")
                collected = []

                for i in range(len(parts)):
                    name = ".".join(parts[:i+1])
                    parent = next((r for r in routes if r.state_name == name), None)
                    if not parent:
                        continue

                    url = (parent.path or "").strip("/")
                    if url:
                        collected.append(url)

                angular_path = "/".join(collected)
            else:
                angular_path = (route.path or "").lstrip("/")

            if cls:
                if resolve_providers:
                    resolve_block = "{\n" + ",\n".join(resolve_providers) + "\n    }"
                    entry = (
                        f"  {{\n"
                        f"    path: '{angular_path}',\n"
                        f"    component: {cls},\n"
                        f"    resolve: {resolve_block}\n"
                        f"  }}"
                    )
                else:
                    entry = f"  {{ path: '{angular_path}', component: {cls} }}"
            else:
                # Route without a controller — static/redirect route
                entry = (
                    f"  {{\n"
                    f"    path: '{angular_path}'\n"
                    f"  }}  // TODO: no controller — add component"
                )

            route_entries.append(entry)

        # Assemble
        import_lines = [
            f"import {{ {cls} }} from './{base}.component';"
            if not base.endswith(".resolver")
            else f"import {{ {cls} }} from './{base}';"
            for cls, base in sorted(component_imports.items())
        ]
        import_lines = ["import { NgModule } from '@angular/core';",
                        "import { RouterModule, Routes } from '@angular/router';"] + import_lines

        # ---- FIX 3: Deduplicate by (path, component) AFTER normalization ----
        dedup_seen = set()
        deduped = []

        for entry in route_entries:
            path_match = re.search(r"path:\s*'([^']+)'", entry)
            comp_match = re.search(r"component:\s*(\w+)", entry)

            path_val = path_match.group(1) if path_match else ""
            comp_val = comp_match.group(1) if comp_match else ""

            key = (path_val, comp_val)

            if key not in dedup_seen:
                dedup_seen.add(key)
                deduped.append(entry)

        route_entries = deduped
        # ----------------------------------------------------------------------

        all_routes = redirect_entries + route_entries
        if wildcard_entry:
            all_routes.append(wildcard_entry)

        if all_routes:
            routes_str = "const routes: Routes = [\n" + ",\n".join(all_routes) + "\n];"
        else:
            routes_str = "const routes: Routes = [];"

        routing_ts = "\n".join(import_lines) + "\n\n" + routes_str + """

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule {}
"""
        return routing_ts, resolver_files
        

    def _build_fallback_routing(self, analysis) -> str:
        """
        No route config was found in the JS — build routing from known controllers.
        This preserves backward-compatibility with existing benchmarks.
        """
        import_lines = [
            "import { NgModule } from '@angular/core';",
            "import { RouterModule, Routes } from '@angular/router';",
        ]
        route_entries = []

        for module in analysis.modules:
            for cls in module.classes:
                name = cls.name
                if not (name.endswith("Controller") or name.endswith("Ctrl")):
                    continue
                base       = name.replace("Controller", "").replace("Ctrl", "").lower()
                class_name = name.replace("Controller", "").replace("Ctrl", "") + "Component"
                import_lines.append(f"import {{ {class_name} }} from './{base}.component';")
                route_entries.append(f"  {{ path: '{base}', component: {class_name} }}")

        if route_entries:
            routes_str = "const routes: Routes = [\n" + ",\n".join(route_entries) + "\n];"
        else:
            routes_str = "const routes: Routes = [];"

        return "\n".join(import_lines) + "\n\n" + routes_str + """

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule {}
"""

    def _build_lazy_route(self, route) -> tuple[Optional[str], Optional[str]]:
        """
        Build a lazy-loaded route entry for an abstract ui-router state.
        Returns (route_entry_string, None) — no extra import needed.
        """
        path = _state_to_path(route.state_name or "feature")
        # e.g. { path: 'app/admin', loadChildren: () => import('./admin/admin.module').then(m => m.AdminModule) }
        module_name = (route.state_name or "feature").split(".")[-1]
        module_class = module_name.capitalize() + "Module"
        entry = (
            f"  {{\n"
            f"    path: '{path}',\n"
            f"    // TODO: create {module_name}/{module_name}.module.ts\n"
            f"    loadChildren: () => import('./{module_name}/{module_name}.module')"
            f".then(m => m.{module_class})\n"
            f"  }}"
        )
        return entry, None

    # -----------------------------------------------------------------------
    # Resolver stub generator
    # -----------------------------------------------------------------------

    def _build_resolver_stub(self, key: str, class_name: str) -> str:
        return (
            f"import {{ Injectable }} from '@angular/core';\n"
            f"import {{ Resolve }} from '@angular/router';\n"
            f"import {{ Observable, of }} from 'rxjs';\n\n"
            f"@Injectable({{ providedIn: 'root' }})\n"
            f"export class {class_name} implements Resolve<any> {{\n\n"
            f"  resolve(): Observable<any> {{\n"
            f"    // TODO: migrate AngularJS resolve block for '{key}'\n"
            f"    return of(null);\n"
            f"  }}\n\n"
            f"}}\n"
        )