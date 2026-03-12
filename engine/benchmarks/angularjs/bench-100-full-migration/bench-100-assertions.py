"""
bench-100-full-coverage — EVUA Engine Comprehensive Assertion Suite
===================================================================
Drop in engine root. Run AFTER:
    python cli.py benchmarks/angularjs/bench-100-full-coverage

Every assertion maps to a specific engine rule or gap.
PASSes = working capabilities.
FAILs  = gaps to fix before research-paper submission.

Sections:
  A  Controller → Component (file generation, @Component, class)
  B  $scope elimination from generated TypeScript
  C  res.data elimination (HttpClient unwraps body automatically)
  D  ngOnInit detection (top-level $scope.fn() calls)
  E  HTTP inlining into method bodies (.then → subscribe, .catch → catchError)
  F  Dynamic URL preservation (BinaryExpression → template literal)
  G  Request body sanitisation ($scope.x → this.x in POST/PUT bodies)
  H  Service → @Injectable (method names preserved, HTTP inlined)
  I  $watch → BehaviorSubject injection
  J  Route migration ($routeProvider → app-routing.module.ts)
  K  AppModule wiring (declarations, providers, imports)
  L  FormsModule auto-detection (ng-model in template)
  M  Template migration (ng-* → Angular syntax)
  N  DI token mapping (custom services injected into constructors)
  O  HttpToHttpClientRule skip (no duplicate stubs)
  P  Directive → Component conversion (DirectiveToComponentRule)
  Q  Filter → Pipe conversion (FilterToPipeRule)
  R  TypeScript compilation (tsc --noEmit on generated project)
  S  Module alias detection (var app = angular.module(...); app.controller(...))
  T  AngularJS 1.5+ .component() detection
  U  $watchCollection / $watchGroup detection
  V  Multi-file ingestion (constructs from directives.js and filters.js)
"""

import sys, tempfile
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# Output directory locator
# ─────────────────────────────────────────────────────────────────────────────

def _find_app_dir() -> Path:
    # go from benchmark file → engine root
    engine_root = Path(__file__).resolve().parents[3]

    candidates = []

    def add_if_exists(p: Path):
        if p.exists():
            candidates.append((p.stat().st_mtime, p))

    # 1️⃣ standard output
    add_if_exists(engine_root / "out" / "angular-app" / "src" / "app")

    # 2️⃣ nested scaffold output
    add_if_exists(engine_root / "out" / "angular-app" / "angular-app" / "src" / "app")

    # 3️⃣ tmp pipeline runs
    out = engine_root / "out"
    if out.exists():
        for d in out.iterdir():
            if d.name.startswith(".tmp_"):
                add_if_exists(d / "angular-app" / "src" / "app")

    # 4️⃣ shadow runs (--diff)
    tmp = Path(tempfile.gettempdir())
    try:
        for d in tmp.iterdir():
            if d.name.startswith("evua_shadow_"):
                add_if_exists(d / "angular-app" / "src" / "app")
    except PermissionError:
        pass

    if not candidates:
        raise FileNotFoundError(
            "Cannot find Angular output directory.\n"
            "Run:\n"
            "    python cli.py benchmarks/angularjs/bench-100-full-migration"
        )

    # newest result wins
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def _scope_in_code(text: str) -> bool:
    """True if $scope appears in executable (non-comment) lines."""
    for line in text.splitlines():
        if line.strip().startswith("//"):
            continue
        if "$scope" in line:
            return True
    return False


def _resdata_in_code(text: str) -> bool:
    """True if res.data appears in executable (non-comment) lines."""
    for line in text.splitlines():
        if line.strip().startswith("//"):
            continue
        if "res.data" in line:
            return True
    return False


# ─────────────────────────────────────────────────────────────────────────────
# Setup
# ─────────────────────────────────────────────────────────────────────────────

try:
    OUT = _find_app_dir()
except FileNotFoundError as e:
    print(f"ERROR: {e}")
    sys.exit(1)

print(f"Output dir : {OUT}")
present = sorted(f.name for f in OUT.iterdir()) if OUT.exists() else []
print(f"Files ({len(present)}): {present}\n")

PASS_LIST, FAIL_LIST = [], []
CAT_STATS: dict[str, dict] = {}


def section(letter: str, title: str):
    print(f"\n{'─'*65}")
    print(f"  [{letter}] {title}")
    print(f"{'─'*65}")


def check(name: str, cond: bool, note: str = "", cat: str = "?"):
    CAT_STATS.setdefault(cat, {"p": 0, "f": 0})
    if cond:
        PASS_LIST.append(name)
        CAT_STATS[cat]["p"] += 1
        print(f"  PASS  {name}")
    else:
        FAIL_LIST.append(name)
        CAT_STATS[cat]["f"] += 1
        suffix = f"  ← {note}" if note else ""
        print(f"  FAIL  {name}{suffix}")


# ─────────────────────────────────────────────────────────────────────────────
# Load every output file we will check
# ─────────────────────────────────────────────────────────────────────────────

# Controllers → Components
userlist   = _read(OUT / "userlist.component.ts")
userdetail = _read(OUT / "userdetail.component.ts")
dashboard  = _read(OUT / "dashboard.component.ts")
product    = _read(OUT / "product.component.ts")
auth       = _read(OUT / "auth.component.ts")
search     = _read(OUT / "search.component.ts")

# Component templates (HTML)
userlist_html   = _read(OUT / "userlist.component.html")
dashboard_html  = _read(OUT / "dashboard.component.html")
userdetail_html = _read(OUT / "userdetail.component.html")

# Services
user_svc = _read(OUT / "userservice.service.ts")
auth_svc = _read(OUT / "authservice.service.ts")

# Infrastructure
routing    = _read(OUT / "app-routing.module.ts")
app_module = _read(OUT / "app.module.ts")


# ═════════════════════════════════════════════════════════════════════════════
# A. CONTROLLER → COMPONENT  (ControllerToComponentRule)
# ═════════════════════════════════════════════════════════════════════════════
section("A", "Controller → Component (file generation)")

for fname, content, ctrl in [
    ("userlist.component.ts",   userlist,   "UserListController"),
    ("userdetail.component.ts", userdetail, "UserDetailController"),
    ("dashboard.component.ts",  dashboard,  "DashboardController"),
    ("product.component.ts",    product,    "ProductController"),
    ("auth.component.ts",       auth,       "AuthController"),
    ("search.component.ts",     search,     "SearchController"),
]:
    check(f"[A] {fname} generated",
          bool(content), f"file missing — {ctrl} not picked up", "A")
    check(f"[A] {fname} has @Component",
          "@Component(" in content, "no @Component decorator", "A")
    check(f"[A] {fname} exports class",
          "export class" in content, "", "A")


# ═════════════════════════════════════════════════════════════════════════════
# B. $scope ELIMINATION
# ═════════════════════════════════════════════════════════════════════════════
section("B", "$scope elimination from generated TypeScript")

for fname, content in [
    ("userlist.component.ts",   userlist),
    ("userdetail.component.ts", userdetail),
    ("dashboard.component.ts",  dashboard),
    ("product.component.ts",    product),
    ("auth.component.ts",       auth),
    ("search.component.ts",     search),
]:
    check(f"[B] no $scope in {fname}",
          not _scope_in_code(content),
          "$scope found in executable lines", "B")


# ═════════════════════════════════════════════════════════════════════════════
# C. res.data ELIMINATION
# ═════════════════════════════════════════════════════════════════════════════
section("C", "res.data elimination (HttpClient returns body directly)")

for fname, content in [
    ("userlist.component.ts",   userlist),
    ("userdetail.component.ts", userdetail),
    ("dashboard.component.ts",  dashboard),
    ("product.component.ts",    product),
    ("userservice.service.ts",  user_svc),
    ("authservice.service.ts",  auth_svc),
]:
    check(f"[C] no res.data in {fname}",
          not _resdata_in_code(content),
          "res.data not removed — HttpClient body-unwrap missing", "C")


# ═════════════════════════════════════════════════════════════════════════════
# D. ngOnInit DETECTION
# ═════════════════════════════════════════════════════════════════════════════
section("D", "ngOnInit generated only when top-level $scope.fn() call exists")

# UserListController: $scope.loadUsers() at bottom → ngOnInit
check("[D] UserListComponent implements OnInit",
      "implements OnInit" in userlist, "missing implements OnInit", "D")
check("[D] UserListComponent has ngOnInit()",
      "ngOnInit()" in userlist, "", "D")
check("[D] ngOnInit calls this.loadUsers()",
      "this.loadUsers()" in userlist, "loadUsers not called in ngOnInit", "D")

# DashboardController: TWO top-level calls → both must be in ngOnInit
check("[D] DashboardComponent implements OnInit",
      "implements OnInit" in dashboard, "", "D")
check("[D] ngOnInit calls this.loadStats()",
      "this.loadStats()" in dashboard, "", "D")
check("[D] ngOnInit calls this.loadActivity() (second top-level call)",
      "this.loadActivity()" in dashboard,
      "only first top-level call captured; second was dropped", "D")

# ProductController: $scope.loadProducts() → ngOnInit
check("[D] ProductComponent implements OnInit",
      "implements OnInit" in product, "", "D")
check("[D] ngOnInit calls this.loadProducts()",
      "this.loadProducts()" in product, "", "D")

# UserDetailController: NO top-level call → NO ngOnInit
check("[D] UserDetailComponent has NO ngOnInit",
      "ngOnInit" not in userdetail,
      "ngOnInit incorrectly generated (no top-level call in source)", "D")

# AuthController: NO top-level call → NO ngOnInit
check("[D] AuthComponent has NO ngOnInit",
      "ngOnInit" not in auth, "", "D")

# SearchController: NO top-level call → NO ngOnInit
check("[D] SearchComponent has NO ngOnInit",
      "ngOnInit" not in search, "", "D")


# ═════════════════════════════════════════════════════════════════════════════
# E. HTTP INLINING (.then → subscribe/map, .catch → catchError)
# ═════════════════════════════════════════════════════════════════════════════
section("E", "HTTP inlining into method bodies")

# UserListController.loadUsers — GET + .then() + .catch()
check("[E] userlist: http.get('/api/users') present",
      "http.get('/api/users')" in userlist, "", "E")
check("[E] userlist: loadUsers has subscribe or pipe",
      ".subscribe(" in userlist or ".pipe(" in userlist, "", "E")
check("[E] userlist: loadUsers has catchError (source had .catch())",
      "catchError" in userlist, "no catchError despite .catch() in source", "E")

# UserListController.deleteUser — DELETE with dynamic URL
check("[E] userlist: deleteUser calls http.delete",
      "http.delete(" in userlist, "", "E")

# UserDetailController.saveUser — PUT + .then() + .catch()
check("[E] userdetail: saveUser calls http.put",
      "http.put(" in userdetail, "", "E")
check("[E] userdetail: saveUser has catchError",
      "catchError" in userdetail, "", "E")

# DashboardController — two separate GETs
check("[E] dashboard: http.get('/api/dashboard/stats') present",
      "/api/dashboard/stats" in dashboard, "", "E")
check("[E] dashboard: http.get('/api/dashboard/activity') present",
      "/api/dashboard/activity" in dashboard, "", "E")

# ProductController — POST with body
check("[E] product: http.post('/api/products') present",
      "http.post('/api/products'" in product, "", "E")

# SearchController — GET + .catch()
check("[E] search: catchError present (source had .catch())",
      "catchError" in search, "", "E")


# ═════════════════════════════════════════════════════════════════════════════
# F. DYNAMIC URL PRESERVATION  (BinaryExpression → template literal or concat)
# ═════════════════════════════════════════════════════════════════════════════
section("F", "Dynamic URL preservation ('/api/users/' + id)")

# UserListController.deleteUser: $http.delete('/api/users/' + id)
check("[F] userlist: /api/users/ fragment in deleteUser URL",
      "/api/users/" in userlist,
      "dynamic URL '/api/users/' + id collapsed to '/'", "F")
check("[F] userlist: http.delete not collapsed to http.delete('/')",
      "http.delete('/')" not in userlist, "", "F")

# UserDetailController.saveUser: $http.put('/api/users/' + id, ...)
check("[F] userdetail: /api/users/ fragment in saveUser URL",
      "/api/users/" in userdetail,
      "dynamic URL '/api/users/' + id collapsed to '/'", "F")
check("[F] userdetail: http.put not collapsed to http.put('/')",
      "http.put('/'," not in userdetail, "", "F")

# UserService.remove: $http.delete('/api/users/' + id)
check("[F] userservice: /api/users/ fragment in remove URL",
      "/api/users/" in user_svc,
      "dynamic URL '/api/users/' + id collapsed to '/'", "F")


# ═════════════════════════════════════════════════════════════════════════════
# G. REQUEST BODY SANITISATION  ($scope.x → this.x)
# ═════════════════════════════════════════════════════════════════════════════
section("G", "Request body sanitisation ($scope.x → this.x)")

# ProductController: $http.post('/api/products', $scope.newProduct)
check("[G] product: no $scope.newProduct in POST body",
      "$scope.newProduct" not in product,
      "$scope.newProduct not sanitised in POST body", "G")
check("[G] product: this.newProduct present in POST body",
      "this.newProduct" in product, "", "G")

# UserDetailController: $http.put('/api/users/' + id, $scope.user)
check("[G] userdetail: no $scope.user in PUT body",
      "$scope.user" not in userdetail,
      "$scope.user not sanitised in PUT body", "G")
check("[G] userdetail: this.user present in PUT body",
      "this.user" in userdetail, "", "G")


# ═════════════════════════════════════════════════════════════════════════════
# H. SERVICE → @INJECTABLE  (ServiceToInjectableRule)
# ═════════════════════════════════════════════════════════════════════════════
section("H", "Service → @Injectable (method names, HTTP inlining)")

check("[H] userservice.service.ts generated",
      bool(user_svc), "UserService not detected/emitted", "H")
check("[H] authservice.service.ts generated",
      bool(auth_svc), "AuthService not detected/emitted", "H")

# Method name preservation — exact names from source
for method in ["getAll", "create", "remove"]:
    check(f"[H] UserService.{method}() preserved exactly",
          f"{method}(" in user_svc, "method renamed or missing", "H")
for method in ["login", "logout"]:
    check(f"[H] AuthService.{method}() preserved exactly",
          f"{method}(" in auth_svc, "", "H")

# No invented names
check("[H] UserService: no fetchUsers() invented",
      "fetchUsers" not in user_svc, "engine invented fetchUsers", "H")
check("[H] UserService: no getUsers() invented",
      "getUsers" not in user_svc, "engine invented getUsers", "H")

# HTTP bodies inlined in service methods
check("[H] UserService.getAll() calls http.get('/api/users')",
      "http.get('/api/users')" in user_svc, "", "H")
check("[H] UserService.create() calls http.post('/api/users')",
      "http.post('/api/users'" in user_svc, "", "H")
check("[H] UserService.remove() calls http.delete",
      "http.delete(" in user_svc, "", "H")
check("[H] UserService.remove() has catchError",
      "catchError" in user_svc, "no catchError despite .catch() in source", "H")
check("[H] AuthService.login() calls http.post('/api/auth/login')",
      "http.post('/api/auth/login'" in auth_svc, "", "H")
check("[H] AuthService.logout() calls http.post('/api/auth/logout')",
      "http.post('/api/auth/logout'" in auth_svc, "", "H")

# Services have @Injectable decorator
check("[H] UserService has @Injectable",
      "@Injectable(" in user_svc, "", "H")
check("[H] AuthService has @Injectable",
      "@Injectable(" in auth_svc, "", "H")


# ═════════════════════════════════════════════════════════════════════════════
# I. $watch → BehaviorSubject  (SimpleWatchToRxjsRule)
# ═════════════════════════════════════════════════════════════════════════════
section("I", "$watch → BehaviorSubject injection")

# UserListController has $scope.$watch('loading', ...) → shallow watch
check("[I] BehaviorSubject import injected into userlist.component.ts",
      "BehaviorSubject" in userlist,
      "SimpleWatchToRxjsRule did not inject BehaviorSubject", "I")
check("[I] BehaviorSubject field present in UserListComponent class body",
      "new BehaviorSubject" in userlist, "", "I")

# DashboardController has $scope.$watch('filter', ...)
check("[I] BehaviorSubject import injected into dashboard.component.ts",
      "BehaviorSubject" in dashboard, "", "I")

# No $watch raw syntax left in generated code
check("[I] no raw $watch left in userlist.component.ts",
      "$watch" not in userlist or "// $watch" in userlist,
      "raw $watch call not removed/commented from output", "I")


# ═════════════════════════════════════════════════════════════════════════════
# J. ROUTE MIGRATION  (RouteMigratorRule)
# ═════════════════════════════════════════════════════════════════════════════
section("J", "Route migration ($routeProvider → app-routing.module.ts)")

check("[J] app-routing.module.ts generated",
      bool(routing), "routing file missing", "J")
check("[J] RouterModule present",
      "RouterModule" in routing, "", "J")
check("[J] Routes array present",
      "Routes" in routing, "", "J")
check("[J] /users route present",
      "'/users'" in routing or '"/users"' in routing or "path: 'users'" in routing, "", "J")
check("[J] /dashboard route present",
      "dashboard" in routing, "", "J")
check("[J] /products route present",
      "products" in routing, "", "J")
check("[J] /search route present",
      "search" in routing, "", "J")
check("[J] parameterised /users/:id route present",
      ":id" in routing or "users/:id" in routing,
      "dynamic :id route not detected", "J")
check("[J] otherwise/redirectTo present",
      "redirectTo" in routing or "otherwise" in routing.lower(), "", "J")
check("[J] no raw $routeProvider left in routing file",
      "$routeProvider" not in routing, "", "J")


# ═════════════════════════════════════════════════════════════════════════════
# K. AppModule WIRING  (AppModuleUpdaterRule)
# ═════════════════════════════════════════════════════════════════════════════
section("K", "AppModule wiring (declarations, providers, imports)")

check("[K] app.module.ts generated",
      bool(app_module), "", "K")
check("[K] NgModule decorator present",
      "@NgModule" in app_module, "", "K")
check("[K] BrowserModule in imports",
      "BrowserModule" in app_module, "", "K")
check("[K] AppRoutingModule in imports",
      "AppRoutingModule" in app_module, "", "K")
check("[K] HttpClientModule in imports",
      "HttpClientModule" in app_module, "", "K")
check("[K] UserListComponent declared",
      "UserListComponent" in app_module, "", "K")
check("[K] DashboardComponent declared",
      "DashboardComponent" in app_module, "", "K")
check("[K] ProductComponent declared",
      "ProductComponent" in app_module, "", "K")
check("[K] AuthComponent declared",
      "AuthComponent" in app_module, "", "K")
check("[K] SearchComponent declared",
      "SearchComponent" in app_module, "", "K")
check("[K] UserService provided",
      "UserService" in app_module, "", "K")
check("[K] AuthService provided",
      "AuthService" in app_module, "", "K")


# ═════════════════════════════════════════════════════════════════════════════
# L. FormsModule DETECTION  (AppModuleUpdaterRule reads [(ngModel)] in templates)
# ═════════════════════════════════════════════════════════════════════════════
section("L", "FormsModule auto-detection via [(ngModel)] in component templates")

check("[L] FormsModule in app.module.ts imports",
      "FormsModule" in app_module,
      "FormsModule missing — template with ng-model not detected", "L")
check("[L] FormsModule imported from @angular/forms",
      "@angular/forms" in app_module, "", "L")


# ═════════════════════════════════════════════════════════════════════════════
# M. TEMPLATE MIGRATION  (template_migrator.py)
# ═════════════════════════════════════════════════════════════════════════════
section("M", "Template migration (ng-* attributes → Angular syntax)")

# The engine migrates templates when it finds a matching templateUrl file.
# dashboard.html maps to DashboardController.

check("[M] dashboard.component.html generated",
      bool(dashboard_html), "template HTML not generated", "M")
check("[M] userlist.component.html generated",
      bool(userlist_html), "", "M")

if dashboard_html:
    check("[M] ng-if → *ngIf in dashboard template",
          "*ngIf" in dashboard_html, "ng-if not migrated", "M")
    check("[M] ng-repeat → *ngFor in dashboard template",
          "*ngFor" in dashboard_html, "ng-repeat not migrated", "M")
    check("[M] ng-click → (click) in dashboard template",
          "(click)" in dashboard_html, "ng-click not migrated", "M")
    check("[M] ng-class → [ngClass] in dashboard template",
          "[ngClass]" in dashboard_html, "ng-class not migrated", "M")
    check("[M] ng-show → *ngIf (migrated from ng-show)",
          "migrated from ng-show" in dashboard_html or "*ngIf" in dashboard_html,
          "ng-show not migrated", "M")
    check("[M] ng-hide → *ngIf with !()",
          "!(" in dashboard_html, "ng-hide not migrated", "M")
    check("[M] ng-model → [(ngModel)] in dashboard template",
          "[(ngModel)]" in dashboard_html, "ng-model not migrated", "M")
    check("[M] ng-change → (change) in dashboard template",
          "(change)" in dashboard_html, "ng-change not migrated", "M")
    check("[M] ng-style → [ngStyle] in dashboard template",
          "[ngStyle]" in dashboard_html, "ng-style not migrated", "M")
    check("[M] ng-href → [href] in dashboard template",
          "[href]" in dashboard_html, "ng-href not migrated", "M")
    check("[M] ng-src → [src] in dashboard template",
          "[src]" in dashboard_html, "ng-src not migrated", "M")
    check("[M] ng-disabled → [disabled] in dashboard template",
          "[disabled]" in dashboard_html, "ng-disabled not migrated", "M")
    check("[M] ng-readonly → [readOnly] in dashboard template",
          "[readOnly]" in dashboard_html, "ng-readonly not migrated", "M")
    check("[M] limitTo → slice pipe in dashboard template",
          "slice" in dashboard_html, "limitTo not rewritten to slice", "M")
    check("[M] orderBy flagged with TODO in dashboard template",
          "TODO" in dashboard_html or "orderBy" not in dashboard_html,
          "orderBy left as-is without TODO comment", "M")
    check("[M] no raw ng-repeat left in dashboard template",
          "ng-repeat" not in dashboard_html, "ng-repeat not fully removed", "M")
    check("[M] no raw ng-if left in dashboard template",
          "ng-if" not in dashboard_html, "ng-if not fully removed", "M")

if userlist_html:
    check("[M] ng-model → [(ngModel)] in userlist template",
          "[(ngModel)]" in userlist_html, "", "M")
    check("[M] ng-submit → (submit) in userlist template",
          "(submit)" in userlist_html, "ng-submit not migrated", "M")
    check("[M] ng-blur → (blur) in userlist template",
          "(blur)" in userlist_html, "ng-blur not migrated", "M")
    check("[M] ng-keyup → (keyup) in userlist template",
          "(keyup)" in userlist_html, "ng-keyup not migrated", "M")
    check("[M] ng-checked → [checked] in userlist template",
          "[checked]" in userlist_html, "ng-checked not migrated", "M")
    check("[M] ng-value → [value] in userlist template",
          "[value]" in userlist_html, "ng-value not migrated", "M")
    check("[M] filter pipe flagged with TODO in userlist template",
          "TODO" in userlist_html or "filter" not in userlist_html,
          "filter pipe left as-is without TODO comment", "M")
    check("[M] no raw ng-show left in userlist template",
          "ng-show" not in userlist_html, "ng-show not fully removed", "M")
    check("[M] no raw ng-hide left in userlist template",
          "ng-hide" not in userlist_html, "ng-hide not fully removed", "M")


# ═════════════════════════════════════════════════════════════════════════════
# N. DI TOKEN MAPPING  (di_mapper.py → constructor params)
# ═════════════════════════════════════════════════════════════════════════════
section("N", "DI token mapping (custom service → typed constructor param)")

# AuthController uses 'AuthService' (custom DI token)
check("[N] AuthComponent constructor has AuthService param",
      "AuthService" in auth,
      "custom DI token AuthService not mapped to constructor param", "N")
check("[N] AuthComponent imports AuthService",
      "import" in auth and "AuthService" in auth, "", "N")

# SearchController uses '$location' (known DI token → Router)
check("[N] SearchComponent has Router or Location param ($location token)",
      "Router" in search or "Location" in search,
      "$location not mapped — check di_mapper.py KNOWN_DI", "N")

# UserListController uses only $scope and $http
check("[N] UserListComponent has HttpClient constructor param",
      "HttpClient" in userlist, "", "N")


# ═════════════════════════════════════════════════════════════════════════════
# O. HttpToHttpClientRule SKIP (no duplicate service stubs)
# ═════════════════════════════════════════════════════════════════════════════
section("O", "HttpToHttpClientRule skips already-inlined calls (no duplicate stubs)")

# If ServiceToInjectableRule already inlined the HTTP calls,
# HttpToHttpClientRule must NOT create a second service stub file.
dup_user = (OUT / "user.service.ts").exists()   # NOT userservice.service.ts
dup_auth = (OUT / "auth.service.ts").exists()

check("[O] no duplicate user.service.ts stub (HttpToHttpClient skipped)",
      not dup_user,
      "HttpToHttpClientRule created duplicate user.service.ts instead of skipping", "O")
check("[O] no duplicate auth.service.ts stub",
      not dup_auth, "", "O")


# ═════════════════════════════════════════════════════════════════════════════
# ═════════════════════════════════════════════════════════════════════════════
# P. DIRECTIVE → COMPONENT CONVERSION  (DirectiveToComponentRule implemented)
# ═════════════════════════════════════════════════════════════════════════════
section("P", "Directive → Component conversion (DirectiveToComponentRule)")

usercard_comp        = _read(OUT / "usercard.component.ts")
usercard_html        = _read(OUT / "usercard.component.html")
loadingspinner_comp  = _read(OUT / "loadingspinner.component.ts")
loadingspinner_html  = _read(OUT / "loadingspinner.component.html")
statusbadge_comp     = _read(OUT / "statusbadge.component.ts")
statusbadge_html     = _read(OUT / "statusbadge.component.html")
app_module_p         = _read(OUT / "app.module.ts")

# File generation
check("[P] usercard.component.ts generated", bool(usercard_comp), "usercard.component.ts not found", "P")
check("[P] usercard.component.html generated", bool(usercard_html), "usercard.component.html not found", "P")
check("[P] loadingspinner.component.ts generated", bool(loadingspinner_comp), "loadingspinner.component.ts not found", "P")
check("[P] loadingspinner.component.html generated", bool(loadingspinner_html), "loadingspinner.component.html not found", "P")
check("[P] statusbadge.component.ts generated", bool(statusbadge_comp), "statusbadge.component.ts not found", "P")
check("[P] statusbadge.component.html generated", bool(statusbadge_html), "statusbadge.component.html not found", "P")

# @Component decorator
check("[P] usercard.component.ts has @Component", "@Component" in usercard_comp, "missing @Component", "P")
check("[P] loadingspinner.component.ts has @Component", "@Component" in loadingspinner_comp, "missing @Component", "P")
check("[P] statusbadge.component.ts has @Component", "@Component" in statusbadge_comp, "missing @Component", "P")

# export class
check("[P] usercard.component.ts exports class", "export class" in usercard_comp, "missing export class", "P")
check("[P] loadingspinner.component.ts exports class", "export class" in loadingspinner_comp, "missing export class", "P")
check("[P] statusbadge.component.ts exports class", "export class" in statusbadge_comp, "missing export class", "P")

# @Input() from scope bindings — userCard: {user:'='}, statusBadge: {status:'@', label:'@'}
check("[P] usercard: @Input() scope binding present", "@Input()" in usercard_comp, "missing @Input() in usercard", "P")
check("[P] statusbadge: @Input() scope bindings present", "@Input()" in statusbadge_comp, "missing @Input() in statusbadge", "P")

# AppModule declarations
check("[P] UserCardComponent declared in app.module.ts", "UserCardComponent" in app_module_p, "UserCardComponent missing from module", "P")
check("[P] LoadingSpinnerComponent declared in app.module.ts", "LoadingSpinnerComponent" in app_module_p, "LoadingSpinnerComponent missing from module", "P")
check("[P] StatusBadgeComponent declared in app.module.ts", "StatusBadgeComponent" in app_module_p, "StatusBadgeComponent missing from module", "P")


# ═════════════════════════════════════════════════════════════════════════════
# Q. FILTER → PIPE CONVERSION  (DirectiveToPipeRule implemented)
# ═════════════════════════════════════════════════════════════════════════════
section("Q", "Filter → Pipe conversion (FilterToPipeRule)")

capitalize_pipe  = _read(OUT / "capitalize.pipe.ts")
truncate_pipe    = _read(OUT / "truncate.pipe.ts")
currfmt_pipe     = _read(OUT / "currencyformat.pipe.ts")
app_module_q     = _read(OUT / "app.module.ts")

# File generation
check("[Q] capitalize.pipe.ts generated", bool(capitalize_pipe), "capitalize.pipe.ts not found", "Q")
check("[Q] truncate.pipe.ts generated", bool(truncate_pipe), "truncate.pipe.ts not found", "Q")
check("[Q] currencyformat.pipe.ts generated", bool(currfmt_pipe), "currencyformat.pipe.ts not found", "Q")

# @Pipe decorator
check("[Q] capitalize.pipe.ts has @Pipe", "@Pipe" in capitalize_pipe, "missing @Pipe", "Q")
check("[Q] truncate.pipe.ts has @Pipe", "@Pipe" in truncate_pipe, "missing @Pipe", "Q")
check("[Q] currencyformat.pipe.ts has @Pipe", "@Pipe" in currfmt_pipe, "missing @Pipe", "Q")

# Pipe names match filter names
check("[Q] capitalize pipe name correct", "'capitalize'" in capitalize_pipe or '"capitalize"' in capitalize_pipe, "pipe name wrong", "Q")
check("[Q] truncate pipe name correct", "'truncate'" in truncate_pipe or '"truncate"' in truncate_pipe, "pipe name wrong", "Q")
check("[Q] currencyFormat pipe name correct", "'currencyFormat'" in currfmt_pipe or '"currencyFormat"' in currfmt_pipe, "pipe name wrong", "Q")

# PipeTransform + transform()
check("[Q] capitalize.pipe.ts implements PipeTransform", "PipeTransform" in capitalize_pipe, "missing PipeTransform", "Q")
check("[Q] capitalize.pipe.ts has transform() method", "transform(" in capitalize_pipe, "missing transform()", "Q")

# AppModule declarations
check("[Q] CapitalizePipe declared in app.module.ts", "CapitalizePipe" in app_module_q, "CapitalizePipe missing from module", "Q")
check("[Q] TruncatePipe declared in app.module.ts", "TruncatePipe" in app_module_q, "TruncatePipe missing from module", "Q")
check("[Q] CurrencyformatPipe declared in app.module.ts", "CurrencyformatPipe" in app_module_q or "CurrencyFormatPipe" in app_module_q, "CurrencyformatPipe missing from module", "Q")



# ═════════════════════════════════════════════════════════════════════════════
# S. MODULE ALIAS DETECTION  (var app = angular.module(...); app.controller(...))
# ═════════════════════════════════════════════════════════════════════════════
section("S", "Module alias detection (var app = angular.module(...))")

# NotificationController is registered via: app.controller('NotificationController', ...)
# The engine must detect it via the alias map built in Pass 1 of js.py.
notification_comp = _read(OUT / "notification.component.ts")

check("[S] notification.component.ts generated (alias-registered controller detected)",
      bool(notification_comp),
      "NotificationController not detected — alias-based registration not parsed", "S")
check("[S] notification.component.ts has @Component",
      "@Component(" in notification_comp, "missing @Component", "S")
check("[S] notification.component.ts exports class",
      "export class" in notification_comp, "missing export class", "S")
check("[S] NotificationComponent declared in app.module.ts",
      "NotificationComponent" in app_module, "NotificationComponent not wired into AppModule", "S")

# Verify http.get('/api/notifications') is inlined correctly
check("[S] notification: http.get('/api/notifications') inlined",
      "/api/notifications" in notification_comp,
      "HTTP call not inlined — body scanner missed alias-registered controller", "S")

# ngOnInit from $scope.loadNotifications() top-level call
check("[S] NotificationComponent implements OnInit",
      "implements OnInit" in notification_comp, "missing implements OnInit", "S")
check("[S] ngOnInit calls this.loadNotifications()",
      "this.loadNotifications()" in notification_comp, "loadNotifications missing from ngOnInit", "S")


# ═════════════════════════════════════════════════════════════════════════════
# T. .component() DETECTION  (AngularJS 1.5+ component syntax)
# ═════════════════════════════════════════════════════════════════════════════
section("T", "AngularJS 1.5+ .component() detection")

# app.component('userProfile', { template: ..., controller: [..., function() {...}] })
# Engine must detect this as a component and generate userprofile.component.ts
userprofile_comp = _read(OUT / "userprofile.component.ts")

check("[T] userprofile.component.ts generated (.component() detected)",
      bool(userprofile_comp),
      "app.component('userProfile') not detected — .component() support missing", "T")
check("[T] userprofile.component.ts has @Component",
      "@Component(" in userprofile_comp, "missing @Component", "T")
check("[T] UserprofileComponent declared in app.module.ts",
      "UserprofileComponent" in app_module, "UserprofileComponent not wired into AppModule", "T")


# ═════════════════════════════════════════════════════════════════════════════
# U. $watchCollection / $watchGroup DETECTION
# ═════════════════════════════════════════════════════════════════════════════
section("U", "$watchCollection / $watchGroup detection")

# NotificationController uses both $watchCollection and $watchGroup.
# Engine must detect them (Phase 3 fix in scan_fn) and produce
# appropriate BehaviorSubject / comment output.

check("[U] $watchCollection detected — BehaviorSubject or comment in notification component",
      "BehaviorSubject" in notification_comp or "$watchCollection" in notification_comp or
      "watchCollection" in notification_comp.lower(),
      "$watchCollection not reflected in output (missing from watch_depths)", "U")

check("[U] $watchGroup detected — BehaviorSubject or comment in notification component",
      "BehaviorSubject" in notification_comp or "watchGroup" in notification_comp.lower() or
      "group" in notification_comp.lower(),
      "$watchGroup not reflected in output (missing from watch_depths)", "U")

# The engine must not leave raw $watchCollection / $watchGroup in generated TS
check("[U] no raw $watchCollection in notification.component.ts",
      "$watchCollection" not in notification_comp,
      "raw $watchCollection left in generated TypeScript", "U")
check("[U] no raw $watchGroup in notification.component.ts",
      "$watchGroup" not in notification_comp,
      "raw $watchGroup left in generated TypeScript", "U")


# ═════════════════════════════════════════════════════════════════════════════
# V. MULTI-FILE INGESTION  (constructs from directives.js and filters.js)
# ═════════════════════════════════════════════════════════════════════════════
section("V", "Multi-file ingestion (directives.js / filters.js constructs detected)")

# directives.js contains: angular.module('bench100App').directive('statusBadge', ...)
# This is a CHAINED call (no alias), so it should be detected with or without Phase 3.
# If P (directive → component) is implemented, statusbadge.component.ts will exist.
# Here we measure raw detection: was the directive at minimum SEEN by the analyzer?

# The cleanest measurable proxy: statusbadge.component.ts was generated (P rule ran on it)
# or the engine logs detected it. Since the bench can only read output files, we use:
# statusbadge.component.ts presence (already checked in P) as the detection proxy.
# Here we add a DISTINCT check: the statusBadge source came from directives.js (not app.js).

_statusbadge_in_p = bool(_read(OUT / "statusbadge.component.ts"))

check("[V] statusBadge (from directives.js) resulted in output component",
      _statusbadge_in_p,
      "directives.js constructs not ingested — multi-file processing failed", "V")

# filters.js contains: angular.module('bench100App').filter('currencyFormat', ...)
# currencyformat.pipe.ts was already checked in Q; here we confirm multi-file is why.
_currfmt_in_q = bool(_read(OUT / "currencyformat.pipe.ts"))

check("[V] currencyFormat (from filters.js) resulted in output pipe",
      _currfmt_in_q,
      "filters.js constructs not ingested — multi-file processing failed", "V")

# routes.js is intentionally empty — engine must not crash on it
check("[V] empty routes.js did not prevent other files from being processed",
      bool(routing),
      "routing file missing — empty routes.js may have blocked pipeline", "V")



# =============================================================================
# SECTION W — Chained .component() (angular.module('x').component(...))
#   js.py sets is_component=True; iter_controllers yields it;
#   naming: name.lower() => phonelist.component.ts / PhonelistComponent
# =============================================================================
section("W", "Chained .component() -- angular.module('x').component(...)")

_phonelist_ts = _read(OUT / "phonelist.component.ts")
_appmod_w     = _read(OUT / "app.module.ts") or ""

check("[W] phonelist.component.ts generated (chained .component() detected)",
      bool(_phonelist_ts),
      "file missing -- angular.module('x').component() not detected", "W")

if _phonelist_ts:
    check("[W] phonelist.component.ts has @Component",
          "@Component(" in _phonelist_ts, "no @Component", "W")
    check("[W] PhonelistComponent declared in app.module.ts",
          "PhonelistComponent" in _appmod_w, "PhonelistComponent not in app.module.ts", "W")
    check("[W] loadPhones method present",
          "loadPhones" in _phonelist_ts, "loadPhones missing", "W")
    check("[W] ngOnInit present (self.loadPhones() init call detected)",
          "ngOnInit" in _phonelist_ts, "ngOnInit missing", "W")


# =============================================================================
# SECTION X -- .factory() detection
#   Naming: raw_name.lower() => phoneservice.service.ts (no hyphens)
# =============================================================================
section("X", ".factory() detection")

_phonesvc_ts = _read(OUT / "phoneservice.service.ts")
_appmod_x    = _read(OUT / "app.module.ts") or ""

check("[X] phoneservice.service.ts generated (.factory() detected)",
      bool(_phonesvc_ts),
      "file missing -- .factory() not picked up by ServiceToInjectableRule", "X")

if _phonesvc_ts:
    check("[X] phoneservice.service.ts has @Injectable",
          "@Injectable(" in _phonesvc_ts, "no @Injectable", "X")
    check("[X] PhoneService provided in app.module.ts",
          "PhoneService" in _appmod_x, "PhoneService not in app.module.ts", "X")


# =============================================================================
# SECTION Y -- self/vm alias methods + ngOnInit in .component() controller
#   var self = this; self.loadDetail = fn; self.setImage = fn; self.loadDetail()
#   Naming: phonedetail.component.ts / PhonedetailComponent
# =============================================================================
section("Y", "self/vm alias methods + ngOnInit in .component() controllers")

_phonedetail_ts = _read(OUT / "phonedetail.component.ts")

check("[Y] phonedetail.component.ts generated (self-alias .component() detected)",
      bool(_phonedetail_ts),
      "file missing -- self.method .component() controller not detected", "Y")

if _phonedetail_ts:
    check("[Y] loadDetail method present",
          "loadDetail" in _phonedetail_ts, "loadDetail missing", "Y")
    check("[Y] setImage method present",
          "setImage" in _phonedetail_ts, "setImage missing", "Y")
    check("[Y] ngOnInit present (self.loadDetail() init call detected)",
          "ngOnInit" in _phonedetail_ts, "ngOnInit missing", "Y")


#    This is the ultimate proof that the engine produces real Angular —
#    not just syntactically plausible TypeScript.
# ═════════════════════════════════════════════════════════════════════════════
section("R", "TypeScript compilation (tsc --noEmit) — generated project compiles cleanly")

import subprocess as _subprocess
import sys as _sys

# Locate the generated project root (one level up from OUT which is src/app)
# OUT = .../angular-app/src/app  → project root = .../angular-app
_project_root = OUT.parent.parent  # angular-app/

_tsconfig = _project_root / "tsconfig.app.json"
if not _tsconfig.exists():
    _tsconfig = _project_root / "tsconfig.json"

if not _tsconfig.exists():
    check("[R] tsconfig.app.json found in generated project",
          False, f"no tsconfig found under {_project_root}", "R")
else:
    check("[R] tsconfig.app.json found in generated project", True, cat="R")

    # --- ensure node_modules (npm install if missing) ---
    _node_modules = _project_root / "node_modules"
    _npm_ok = True
    if not _node_modules.exists():
        _npm = "npm.cmd" if _sys.platform == "win32" else "npm"
        print(f"  [R] node_modules not found — running: {_npm} install")
        print(f"  [R] (this may take 30-60 seconds on first run...)")
        try:
            _npm_result = _subprocess.run(
                [_npm, "install"],
                capture_output=True, text=True,
                cwd=str(_project_root),
                timeout=300,
            )
            if _npm_result.returncode == 0:
                print("  [R] npm install OK")
            else:
                print(f"  [R] npm install failed (rc={_npm_result.returncode})")
                for _l in _npm_result.stderr.splitlines()[:5]:
                    print(f"  [R]   {_l}")
                _npm_ok = False
                check("[R] npm install succeeded (node_modules present)",
                      False, "npm install failed — cannot run tsc", "R")
        except FileNotFoundError:
            _npm_ok = False
            check("[R] npm install succeeded (node_modules present)",
                  False, "npm not found — install Node.js from https://nodejs.org", "R")
        except _subprocess.TimeoutExpired:
            _npm_ok = False
            check("[R] npm install succeeded (node_modules present)",
                  False, "npm install timed out after 5 minutes", "R")
    else:
        check("[R] node_modules present (npm install not needed)", True, cat="R")

    if _npm_ok:
        # --- find tsc ---
        _tsc = "tsc.cmd" if _sys.platform == "win32" else "tsc"
        _tsc_found = False
        for _candidate in [_tsc, "npx.cmd tsc" if _sys.platform == "win32" else "npx tsc"]:
            try:
                _v = _subprocess.run(
                    _candidate.split() + ["--version"],
                    capture_output=True, text=True, timeout=15,
                    cwd=str(_project_root),
                )
                if _v.returncode == 0:
                    _tsc_cmd = _candidate.split()
                    _tsc_found = True
                    print(f"  [R] tsc: {_v.stdout.strip()} ({_candidate})")
                    break
            except (FileNotFoundError, _subprocess.TimeoutExpired):
                continue

        if not _tsc_found:
            check("[R] tsc --noEmit exits 0 (generated Angular compiles)",
                  False,
                  "tsc not found — run: npm install -g typescript", "R")
        else:
            _result = _subprocess.run(
                _tsc_cmd + ["--noEmit", "--project", str(_tsconfig)],
                capture_output=True, text=True,
                cwd=str(_project_root),
                timeout=120,
            )
            _err_lines = [l for l in _result.stdout.splitlines() if "error TS" in l]
            _n = len(_err_lines)

            if _result.returncode == 0:
                check("[R] tsc --noEmit exits 0 (generated Angular compiles)", True, cat="R")
            else:
                # Categorise errors so the failure message is diagnostic
                _missing = [l for l in _err_lines if "TS2307" in l or "TS2306" in l]
                _strict  = [l for l in _err_lines
                            if any(c in l for c in ["TS2564","TS2531","TS2532","TS7006","TS7034"])]
                _struct  = [l for l in _err_lines
                            if any(c in l for c in ["TS2304","TS2339","TS2345","TS2322"])]
                _other   = [l for l in _err_lines
                            if l not in _missing + _strict + _struct]

                _detail = (
                    f"{_n} error(s): "
                    f"missing_import={len(_missing)} "
                    f"strict={len(_strict)} "
                    f"structural={len(_struct)} "
                    f"other={len(_other)}"
                )
                check("[R] tsc --noEmit exits 0 (generated Angular compiles)",
                      False, _detail, "R")

                # Print first 15 errors for diagnosis
                print(f"  [R] First errors:")
                for _el in _err_lines[:15]:
                    # Trim the path to just filename
                    import re as _re
                    _m = _re.search(r"([^/\\]+\.ts)\(", _el)
                    _short = _m.group(1) if _m else _el
                    print(f"  [R]   {_short}")


# ═════════════════════════════════════════════════════════════════════════════
# SUMMARY
# ═════════════════════════════════════════════════════════════════════════════
total_p = len(PASS_LIST)
total_f = len(FAIL_LIST)
total   = total_p + total_f

print(f"\n" + "=" * 65)
print(f"  OVERALL: {total_p}/{total} passed  |  {total_f} failed")
print("=" * 65)

CAT_LABELS = {
    "A": "Controller → Component (file gen)",
    "B": "$scope elimination",
    "C": "res.data elimination",
    "D": "ngOnInit detection",
    "E": "HTTP inlining (.then/.catch)",
    "F": "Dynamic URL preservation",
    "G": "Request body sanitisation",
    "H": "Service → @Injectable",
    "I": "$watch → BehaviorSubject",
    "J": "Route migration",
    "K": "AppModule wiring",
    "L": "FormsModule detection",
    "M": "Template migration",
    "N": "DI token mapping",
    "O": "No duplicate stubs",
    "P": "Directive → Component conversion",
    "Q": "Filter → Pipe conversion",
    "R": "TypeScript compilation (tsc --noEmit)",
    "S": "Module alias detection (var app = angular.module(...))",
    "T": "AngularJS 1.5+ .component() detection",
    "U": "$watchCollection / $watchGroup detection",
    "V": "Multi-file ingestion (directives.js / filters.js)",
    "W": "Chained .component() -- angular.module('x').component(...)",
    "X": ".factory() detection",
    "Y": "self/vm alias methods + ngOnInit in .component() controllers",
}

print("\nCategory breakdown:")
for cat in "ABCDEFGHIJKLMNOPQRSTUVWXY":
    if cat not in CAT_STATS:
        continue
    p = CAT_STATS[cat]["p"]
    f = CAT_STATS[cat]["f"]
    t = p + f
    bar    = "✓" * p + "✗" * f
    label  = CAT_LABELS.get(cat, cat)
    status = "DONE" if f == 0 else "GAPS"
    print(f"  {status}  [{cat}] {label:40s} {p:2d}/{t:2d}  {bar}")

print()
real_fails = list(FAIL_LIST)

if real_fails:
    print(f"FAILURES ({len(real_fails)}) — bugs to fix:")
    for n in real_fails:
        print(f"  ✗ {n}")
    print()

print("SUBMISSION READINESS:")
if not real_fails:
    print("  ✅ All implemented features work correctly.")
    print("  → Engine is ready for paper submission.")
    r_stats = CAT_STATS.get("R", {})
    if r_stats.get("p", 0) > 0:
        print("  → tsc --noEmit ✅ — generated Angular compiles cleanly.")
else:
    print(f"  ❌ {len(real_fails)} features have bugs — fix before submission.")

sys.exit(0 if not real_fails else 1)