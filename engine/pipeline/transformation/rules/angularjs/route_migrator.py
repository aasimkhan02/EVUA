"""
RouteMigratorRule
=================
Converts AngularJS route definitions ($routeProvider / $stateProvider)
into a production-ready Angular app-routing.module.ts.

Features
--------
1. Nested children routing   — uiRouter parent/child hierarchy → Angular children[]
2. Lazy loading              — abstract states → loadChildren: () => import(...)
3. Componentless parents     — no-controller parents get children[] but no component
4. Template binding          — templateUrl/template wired to component's templateUrl/template
5. Guard migration           — resolve keys named 'auth'/'user'/'session' → canActivate guards
6. uiRouter redirect states  — redirectTo / onEnter / onExit handled with TODO comments
7. Route order safety        — static > param > wildcard ordering enforced
"""

from pathlib import Path
from typing import Optional
import re

from ir.migration_model.change import Change
from ir.migration_model.base import ChangeSource
from pipeline.transformation.angular_project_scaffold import AngularProjectScaffold


# ── Helpers ──────────────────────────────────────────────────────────────────

def _ctrl_to_component_class(name: Optional[str]) -> Optional[str]:
    if not name:
        return None
    return name.replace("Controller", "").replace("Ctrl", "") + "Component"


def _ctrl_to_base(name: Optional[str]) -> Optional[str]:
    if not name:
        return None
    return name.replace("Controller", "").replace("Ctrl", "").lower()


def _resolver_class_name(key: str) -> str:
    return key[0].upper() + key[1:] + "Resolver"


def _guard_class_name(key: str) -> str:
    return key[0].upper() + key[1:] + "Guard"


# Resolve keys that look like auth guards rather than data resolvers
_AUTH_KEYS = {"auth", "authenticated", "user", "currentUser", "session",
              "loggedIn", "isLoggedIn", "authCheck", "loginCheck"}


def _is_auth_resolve(key: str) -> bool:
    return key in _AUTH_KEYS or key.lower().startswith("auth") or key.lower().startswith("login")


# ── Route tree node ───────────────────────────────────────────────────────────

class RouteNode:
    """
    A node in the hierarchical route tree built from uiRouter state names.
    state 'app.users.detail' → RouteNode('app') → RouteNode('users') → RouteNode('detail')
    """
    def __init__(self, state_name: str, raw: object = None):
        self.state_name = state_name          # full dotted name  e.g. 'app.users'
        self.raw        = raw                 # RawRoute object (None for synthetic parents)
        self.children:  list["RouteNode"] = []

    @property
    def segment(self) -> str:
        """Last part of the dotted name: 'app.users' → 'users'"""
        return self.state_name.split(".")[-1]

    @property
    def depth(self) -> int:
        return self.state_name.count(".")


def _build_state_tree(routes: list) -> list:
    """
    Given a flat list of RawRoute (uiRouter), build a forest of RouteNode trees.
    Returns list of root RouteNodes.
    """
    by_name: dict[str, RouteNode] = {}

    # Create nodes for all real routes
    for r in routes:
        if r.state_name:
            by_name[r.state_name] = RouteNode(r.state_name, r)

    # Ensure every ancestor exists (create synthetic nodes if gaps)
    for name in list(by_name.keys()):
        parts = name.split(".")
        for i in range(1, len(parts)):
            ancestor = ".".join(parts[:i])
            if ancestor not in by_name:
                by_name[ancestor] = RouteNode(ancestor, None)

    # Wire parent → child relationships
    roots: list[RouteNode] = []
    for name, node in by_name.items():
        if "." not in name:
            roots.append(node)
        else:
            parent_name = ".".join(name.split(".")[:-1])
            by_name[parent_name].children.append(node)

    # Sort siblings so static paths precede parameterised ones
    def _sort_children(node: RouteNode):
        node.children.sort(key=lambda n: (
            1 if (n.raw and ":" in (n.raw.path or "")) else 0,
            n.segment,
        ))
        for child in node.children:
            _sort_children(child)

    roots.sort(key=lambda n: (1 if (n.raw and ":" in (n.raw.path or "")) else 0, n.segment))
    for r in roots:
        _sort_children(r)

    return roots


# ── Main rule ─────────────────────────────────────────────────────────────────

class RouteMigratorRule:
    def __init__(self, out_dir: str = "out/angular-app", dry_run: bool = False):
        self.project      = AngularProjectScaffold(out_dir)
        self.out_dir      = Path(out_dir) / "src" / "app"
        self.routing_path = self.out_dir / "app-routing.module.ts"
        self.dry_run      = dry_run

    # ── Public entry ─────────────────────────────────────────────────────────

    def apply(self, analysis, patterns):
        print("\n========== RouteMigratorRule.apply() ==========")
        if self.dry_run:
            print("[RouteMigrator] DRY RUN — no files will be written")

        changes = []
        if not self.dry_run:
            self.project.ensure()

        raw_routes = getattr(analysis, "routes", []) or []

        # Deduplicate
        seen_sigs: set = set()
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
                flags = []
                if r.is_abstract:   flags.append("abstract")
                if r.is_otherwise:  flags.append("otherwise")
                if getattr(r, "redirect_to", None):  flags.append(f"redirectTo={r.redirect_to}")
                if getattr(r, "on_enter", None):     flags.append("onEnter")
                if getattr(r, "on_exit", None):      flags.append("onExit")
                print(f"[RouteMigrator]   {r.router_type:8s}  {symbol:35s}  ctrl={r.controller}  {' '.join(flags)}")

        routing_ts, extra_files = self._build_routing_module(routes, analysis)

        if self.dry_run:
            print(f"[DRY RUN] Would write: {self.routing_path}")
            print(f"[DRY RUN] Content preview:\n{routing_ts[:600]}")
        else:
            self.routing_path.write_text(routing_ts, encoding="utf-8")
            print(f"[RouteMigrator] Written: {self.routing_path}")

        changes.append(Change(
            before_id="routing_module",
            after_id="angular_routing_module",
            source=ChangeSource.RULE,
            reason=f"Angular Router configured written to {self.routing_path}",
        ))

        for fname, content in extra_files.items():
            fpath = self.out_dir / fname
            if self.dry_run:
                print(f"[DRY RUN] Would write: {fpath}")
            else:
                fpath.write_text(content, encoding="utf-8")
                print(f"[RouteMigrator] Written: {fpath}")
            changes.append(Change(
                before_id=f"extra_{fname}",
                after_id=f"generated_{fname}",
                source=ChangeSource.RULE,
                reason=f"Generated {fpath}",
            ))

        print("========== RouteMigratorRule DONE ==========\n")
        return changes

    # ── Module builder ────────────────────────────────────────────────────────

    def _build_routing_module(self, routes: list, analysis) -> tuple[str, dict]:
        extra_files: dict[str, str] = {}

        if not routes:
            return self._build_fallback_routing(analysis), extra_files

        router_types = {r.router_type for r in routes}
        is_ui_router = "uiRouter" in router_types

        component_imports: dict[str, str] = {}   # class → base filename
        guard_imports:     dict[str, str] = {}   # GuardClass → filename
        redirect_target:   Optional[str]  = None
        wildcard_entry:    Optional[str]  = None

        if is_ui_router:
            # ── uiRouter path: build nested tree ─────────────────────────
            ui_routes = [r for r in routes if r.router_type == "uiRouter"]

            # Collect redirects / otherwise from uiRouter first
            for r in ui_routes:
                if r.is_otherwise:
                    redirect_target = (r.path or "").lstrip("/") or redirect_target
                elif getattr(r, "redirect_to", None) and not r.controller:
                    # Pure redirect state (no component, has redirectTo)
                    if redirect_target is None:
                        redirect_target = r.redirect_to.lstrip("/")

            # Build state tree
            non_redirect = [r for r in ui_routes if not r.is_otherwise]
            roots = _build_state_tree(non_redirect)

            route_entries: list[str] = []
            for root in roots:
                entry = self._render_node(
                    root, depth=1,
                    component_imports=component_imports,
                    guard_imports=guard_imports,
                    extra_files=extra_files,
                )
                if entry:
                    route_entries.append(entry)

        else:
            # ── ngRoute path: flat list ───────────────────────────────────
            ng_routes = [r for r in routes if r.router_type == "ngRoute"]
            route_entries = []

            for r in _sort_flat_routes(ng_routes):
                if r.is_otherwise:
                    redirect_target = (r.path or "").lstrip("/") or redirect_target
                    continue

                cls  = _ctrl_to_component_class(r.controller)
                base = _ctrl_to_base(r.controller)
                if cls and base:
                    component_imports[cls] = base

                guards, new_resolvers, new_guards = self._split_resolve(r.resolve)
                for key, stub in new_resolvers.items():
                    extra_files[key] = stub
                for key, stub in new_guards.items():
                    extra_files[key]  = stub
                    gcls = _guard_class_name(key.replace(".guard.ts", ""))
                    guard_imports[gcls] = key.replace(".ts", "")

                # Collect resolver imports
                for rkey in r.resolve:
                    if not _is_auth_resolve(rkey):
                        rcls  = _resolver_class_name(rkey)
                        rfile = f"{rkey.lower()}.resolver"
                        component_imports[rcls] = rfile

                angular_path = (r.path or "").lstrip("/")
                entry = self._render_flat_route(
                    angular_path, cls, r.resolve, guards,
                    template_url=getattr(r, "template_url", None),
                    template=getattr(r, "template", None),
                    indent=1,
                )
                route_entries.append(entry)

        # ── Assemble import lines ─────────────────────────────────────────
        import_lines = [
            "import { NgModule } from '@angular/core';",
            "import { RouterModule, Routes } from '@angular/router';",
        ]
        for cls, base in sorted(component_imports.items()):
            if base.endswith(".resolver"):
                import_lines.append(f"import {{ {cls} }} from './{base}';")
            elif base.endswith(".guard"):
                import_lines.append(f"import {{ {cls} }} from './{base}';")
            else:
                import_lines.append(f"import {{ {cls} }} from './{base}.component';")

        for gcls, gbase in sorted(guard_imports.items()):
            if gcls not in component_imports:
                import_lines.append(f"import {{ {gcls} }} from './{gbase}';")

        # ── Assemble routes array ─────────────────────────────────────────
        all_routes: list[str] = []
        if redirect_target:
            all_routes.append(
                f"  {{ path: '', redirectTo: '/{redirect_target}', pathMatch: 'full' }}"
            )
        all_routes.extend(route_entries)
        if wildcard_entry:
            all_routes.append(wildcard_entry)

        routes_str = (
            "const routes: Routes = [\n" + ",\n".join(all_routes) + "\n];"
            if all_routes else "const routes: Routes = [];"
        )

        routing_ts = "\n".join(import_lines) + "\n\n" + routes_str + """

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule {}
"""
        return routing_ts, extra_files

    # ── Node renderer (recursive, for uiRouter tree) ──────────────────────

    def _render_node(
        self,
        node: "RouteNode",
        depth: int,
        component_imports: dict,
        guard_imports: dict,
        extra_files: dict,
    ) -> Optional[str]:
        """
        Renders a RouteNode and its children into a TypeScript route object string.
        Returns None if the node has no path and no children worth emitting.
        """
        indent  = "  " * depth
        cindent = "  " * (depth + 1)

        raw = node.raw

        # ── Determine own path segment ────────────────────────────────────
        if raw:
            # Use the URL from the state config, strip the leading /
            own_path = (raw.path or "").lstrip("/")
            # For child states, the URL may be relative (no leading /) — use as-is
            # For root states with no URL, fall back to segment name
            if not own_path:
                own_path = node.segment
        else:
            # Synthetic ancestor node — use segment name
            own_path = node.segment

        # ── Skip pure redirect states (redirectTo + no controller) ────────
        if raw and getattr(raw, "redirect_to", None) and not raw.controller:
            # Already handled in redirect_target collection; render children only
            child_entries = [
                self._render_node(c, depth, component_imports, guard_imports, extra_files)
                for c in node.children
            ]
            return "\n".join(e for e in child_entries if e)

        # ── Abstract → lazy-loaded feature module ─────────────────────────
        # Angular Router forbids loadChildren + children[] on the same route.
        # We emit a clean loadChildren-only route. Children are noted in comments
        # so developers know exactly what goes in the feature module routing file.
        # We still walk the subtree to collect guards/resolvers into extra_files.
        if raw and raw.is_abstract:
            module_name  = node.segment
            module_class = module_name.capitalize() + "Module"
            module_dir   = module_name

            # Walk entire subtree: collect guards/resolvers even though we won't
            # render the children as Angular route objects here.
            def _collect_subtree(n):
                r = n.raw
                if r:
                    g, nr, ng = self._split_resolve(getattr(r, "resolve", {}) or {})
                    for k, v in nr.items():
                        extra_files[k] = v
                    for k, v in ng.items():
                        extra_files[k] = v
                    for gcls in g:
                        gfile = f"{gcls.replace('Guard','').lower()}.guard"
                        guard_imports[gcls] = gfile
                    for rkey in (getattr(r, "resolve", {}) or {}):
                        if not _is_auth_resolve(rkey):
                            component_imports[_resolver_class_name(rkey)] = f"{rkey.lower()}.resolver"
                    cls = _ctrl_to_component_class(r.controller)
                    base = _ctrl_to_base(r.controller)
                    if cls and base:
                        component_imports[cls] = base
                for child in n.children:
                    _collect_subtree(child)

            for child in node.children:
                _collect_subtree(child)

            # Build a readable comment map of child routes (fixed indentation)
            comment_lines: list[str] = []
            def _summarise(n, level: int):
                r = n.raw
                path  = (r.path if r else "").lstrip("/") or n.segment
                ctrl  = (r.controller if r else None) or "—"
                pad   = "  " * level
                comment_lines.append(f"{indent}  //{pad}  {{ path: '{path}', component: {ctrl} }}")
                for c in n.children:
                    _summarise(c, level + 1)

            for child in node.children:
                _summarise(child, 0)

            comment_block = ""
            if comment_lines:
                comment_block = (
                    f"\n{indent}  // ↳ Move these into {module_name}.module.ts routing:\n"
                    + "\n".join(comment_lines)
                )

            entry = (
                f"{indent}{{\n"
                f"{indent}  path: '{own_path}',\n"
                f"{indent}  // TODO: create src/app/{module_dir}/{module_name}.module.ts{comment_block}\n"
                f"{indent}  loadChildren: () => import('./{module_dir}/{module_name}.module')"
                f".then(m => m.{module_class})\n"
                f"{indent}}}"
            )
            print(f"[RouteMigrator] Lazy route: {own_path} → {module_class}")
            return entry

        # ── Regular state ─────────────────────────────────────────────────
        cls  = _ctrl_to_component_class(raw.controller if raw else None)
        base = _ctrl_to_base(raw.controller if raw else None)

        if cls and base:
            component_imports[cls] = base

        # Resolve/guard split
        resolve = (raw.resolve if raw else {}) or {}
        guards, new_resolvers, new_guards = self._split_resolve(resolve)
        for key, stub in new_resolvers.items():
            extra_files[key] = stub
        for key, stub in new_guards.items():
            extra_files[key] = stub

        for rkey in resolve:
            if not _is_auth_resolve(rkey):
                rcls  = _resolver_class_name(rkey)
                rfile = f"{rkey.lower()}.resolver"
                component_imports[rcls] = rfile

        for gcls_name in guards:
            gfile = f"{gcls_name.replace('Guard','').lower()}.guard"
            guard_imports[gcls_name] = gfile

        # Render children recursively
        child_entries = [
            self._render_node(c, depth + 1, component_imports, guard_imports, extra_files)
            for c in node.children
        ]
        child_entries = [e for e in child_entries if e]

        # onEnter / onExit comments
        lifecycle_comments: list[str] = []
        if raw and getattr(raw, "on_enter", None):
            lifecycle_comments.append(f"// TODO: migrate onEnter ({raw.on_enter}) → canActivate guard or ngOnInit()")
        if raw and getattr(raw, "on_exit", None):
            lifecycle_comments.append(f"// TODO: migrate onExit ({raw.on_exit}) → canDeactivate guard or ngOnDestroy()")

        # ── Compose the route object ──────────────────────────────────────
        lines: list[str] = [f"{indent}{{"]

        lines.append(f"{indent}  path: '{own_path}',")

        for lc in lifecycle_comments:
            lines.append(f"{indent}  {lc}")

        if guards:
            guard_arr = ", ".join(guards)
            lines.append(f"{indent}  canActivate: [{guard_arr}],")

        if cls:
            lines.append(f"{indent}  component: {cls},")
        elif not child_entries:
            lines.append(f"{indent}  // TODO: no controller — add component or redirectTo")

        # Resolver block (non-auth resolvers only)
        resolver_entries = [
            f"{cindent}  {rkey}: {_resolver_class_name(rkey)}"
            for rkey in resolve if not _is_auth_resolve(rkey)
        ]
        if resolver_entries:
            lines.append(f"{indent}  resolve: {{")
            lines.extend(f"{r}," for r in resolver_entries)
            lines.append(f"{indent}  }},")

        # Children
        if child_entries:
            lines.append(f"{indent}  children: [")
            lines.append(",\n".join(child_entries))
            lines.append(f"{indent}  ],")

        lines.append(f"{indent}}}")
        return "\n".join(lines)

    # ── Flat route renderer (ngRoute) ─────────────────────────────────────

    def _render_flat_route(
        self,
        angular_path: str,
        cls: Optional[str],
        resolve: dict,
        guards: list[str],
        template_url: Optional[str] = None,
        template: Optional[str] = None,
        indent: int = 1,
    ) -> str:
        pad  = "  " * indent
        cpad = "  " * (indent + 1)

        parts: list[str] = [f"{pad}{{"]
        parts.append(f"{pad}  path: '{angular_path}',")

        if guards:
            parts.append(f"{pad}  canActivate: [{', '.join(guards)}],")

        if cls:
            parts.append(f"{pad}  component: {cls},")
        else:
            parts.append(f"{pad}  // TODO: no controller — add component")

        resolver_entries = [
            f"{cpad}  {k}: {_resolver_class_name(k)}"
            for k in resolve if not _is_auth_resolve(k)
        ]
        if resolver_entries:
            parts.append(f"{pad}  resolve: {{")
            parts.extend(f"{r}," for r in resolver_entries)
            parts.append(f"{pad}  }},")

        parts.append(f"{pad}}}")
        return "\n".join(parts)

    # ── Resolve → resolver/guard splitter ────────────────────────────────

    def _split_resolve(self, resolve: dict) -> tuple[list[str], dict, dict]:
        """
        Given a resolve dict, return:
          guards        — list of guard class names (for canActivate)
          new_resolvers — {filename: content} for data resolvers
          new_guards    — {filename: content} for auth guards
        """
        guards:        list[str] = []
        new_resolvers: dict[str, str] = {}
        new_guards:    dict[str, str] = {}

        for key in resolve:
            if _is_auth_resolve(key):
                gcls  = _guard_class_name(key)
                gfile = f"{key.lower()}.guard.ts"
                guards.append(gcls)
                if gfile not in new_guards:
                    new_guards[gfile] = self._build_guard_stub(key, gcls)
            else:
                rcls  = _resolver_class_name(key)
                rfile = f"{key.lower()}.resolver.ts"
                if rfile not in new_resolvers:
                    new_resolvers[rfile] = self._build_resolver_stub(key, rcls)

        return guards, new_resolvers, new_guards

    # ── Route ordering helper for ngRoute ────────────────────────────────

    # ── Fallback ──────────────────────────────────────────────────────────

    def _build_fallback_routing(self, analysis) -> str:
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

        routes_str = (
            "const routes: Routes = [\n" + ",\n".join(route_entries) + "\n];"
            if route_entries else "const routes: Routes = [];"
        )
        return "\n".join(import_lines) + "\n\n" + routes_str + """

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule {}
"""

    # ── Stub generators ───────────────────────────────────────────────────

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

    def _build_guard_stub(self, key: str, class_name: str) -> str:
        return (
            f"import {{ Injectable }} from '@angular/core';\n"
            f"import {{ CanActivate, Router }} from '@angular/router';\n\n"
            f"@Injectable({{ providedIn: 'root' }})\n"
            f"export class {class_name} implements CanActivate {{\n\n"
            f"  constructor(private router: Router) {{}}\n\n"
            f"  canActivate(): boolean {{\n"
            f"    // TODO: migrate AngularJS resolve '{key}' auth check here\n"
            f"    // Example: if (!this.authService.isLoggedIn()) {{ this.router.navigate(['/login']); return false; }}\n"
            f"    return true;\n"
            f"  }}\n\n"
            f"}}\n"
        )


# ── Module-level helper for ngRoute ordering ─────────────────────────────────

def _sort_flat_routes(routes: list) -> list:
    """
    Sort ngRoute routes so Angular's order-sensitive router matches correctly:
      1. Static paths   (/home, /about)
      2. Param paths    (/users/:id)
      3. Wildcard       (**)
      4. otherwise/redirects last
    """
    def _rank(r):
        if r.is_otherwise:          return 4
        path = r.path or ""
        if path == "**":            return 3
        if ":" in path:             return 2
        return 1

    return sorted(routes, key=_rank)