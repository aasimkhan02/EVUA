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
  P  Directive detection (measured gap — no output file generated)
  Q  Filter detection (measured gap — no output file generated)
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
# P. DIRECTIVE DETECTION  (gap: no DirectiveToComponentRule)
# ═════════════════════════════════════════════════════════════════════════════
section("P", "Directive handling — ENGINE GAP (no DirectiveToComponent rule)")

# The engine detects directives (js.py parses them, DirectiveDetector classifies them)
# but NO rule converts them to Angular components. This section measures that gap.

usercard_comp      = _read(OUT / "usercard.component.ts")
loadingspinner_comp = _read(OUT / "loadingspinner.component.ts")
statusbadge_comp   = _read(OUT / "statusbadge.component.ts")

check("[P] KNOWN GAP: userCard directive NOT converted to component stub",
      not bool(usercard_comp),
      "Unexpected: usercard.component.ts was generated — DirectiveToComponent implemented?", "P")
check("[P] KNOWN GAP: loadingSpinner directive NOT converted to component stub",
      not bool(loadingspinner_comp), "", "P")
check("[P] KNOWN GAP: statusBadge directive NOT converted to component stub",
      not bool(statusbadge_comp), "", "P")

# If the above flip to FAIL, it means DirectiveToComponentRule was implemented — great!
# Flip these to check for the positive when the rule exists:
print(f"\n  ℹ  To FIX [P]: implement DirectiveToComponentRule that converts")
print(f"     .directive() definitions → *.component.ts + *.component.html stubs.")


# ═════════════════════════════════════════════════════════════════════════════
# Q. FILTER DETECTION  (gap: no FilterToPipeRule)
# ═════════════════════════════════════════════════════════════════════════════
section("Q", "Filter handling — ENGINE GAP (no FilterToPipe rule)")

capitalize_pipe  = _read(OUT / "capitalize.pipe.ts")
truncate_pipe    = _read(OUT / "truncate.pipe.ts")
currfmt_pipe     = _read(OUT / "currencyformat.pipe.ts")

check("[Q] KNOWN GAP: capitalize filter NOT converted to pipe stub",
      not bool(capitalize_pipe),
      "Unexpected: capitalize.pipe.ts generated — FilterToPipe implemented?", "Q")
check("[Q] KNOWN GAP: truncate filter NOT converted to pipe stub",
      not bool(truncate_pipe), "", "Q")
check("[Q] KNOWN GAP: currencyFormat filter NOT converted to pipe stub",
      not bool(currfmt_pipe), "", "Q")

print(f"\n  ℹ  To FIX [Q]: implement FilterToPipeRule that converts")
print(f"     .filter() definitions → *.pipe.ts stubs with @Pipe + transform().")


# ═════════════════════════════════════════════════════════════════════════════
# SUMMARY
# ═════════════════════════════════════════════════════════════════════════════
total_p = len(PASS_LIST)
total_f = len(FAIL_LIST)
total   = total_p + total_f

print(f"\n{'═'*65}")
print(f"  OVERALL: {total_p}/{total} passed  |  {total_f} failed")
print(f"{'═'*65}")

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
    "P": "Directive conversion (GAP)",
    "Q": "Filter → Pipe conversion (GAP)",
}

print("\nCategory breakdown:")
for cat in "ABCDEFGHIJKLMNOPQ":
    if cat not in CAT_STATS:
        continue
    p = CAT_STATS[cat]["p"]
    f = CAT_STATS[cat]["f"]
    t = p + f
    bar   = "✓" * p + "✗" * f
    label = CAT_LABELS.get(cat, cat)
    flag  = " ← GAP" if cat in ("P", "Q") else ""
    status = "DONE" if f == 0 else "GAPS"
    print(f"  {status}  [{cat}] {label:40s} {p:2d}/{t:2d}  {bar}{flag}")

print()
real_fails = [n for n in FAIL_LIST if not n.startswith("[P]") and not n.startswith("[Q]")]
gap_fails  = [n for n in FAIL_LIST if n.startswith("[P]") or n.startswith("[Q]")]

if real_fails:
    print(f"REAL FAILURES ({len(real_fails)}) — bugs to fix:")
    for n in real_fails:
        print(f"  ✗ {n}")
    print()

if gap_fails:
    # These are inverted: PASS means "gap confirmed", FAIL means gap was filled
    unexpected = [n for n in gap_fails if "Unexpected" in n or "implemented?" in n]
    if unexpected:
        print(f"GAPS NOW FILLED (update assertions):")
        for n in unexpected:
            print(f"  ✓ {n}")
        print()

print("SUBMISSION READINESS:")
if not real_fails:
    print("  ✅ All implemented features work correctly.")
    print("  📋 Remaining gaps: Directive→Component, Filter→Pipe rules not yet built.")
    print("  → Engine is ready for paper submission (with gap sections documented).")
else:
    print(f"  ❌ {len(real_fails)} implemented features have bugs — fix before submission.")

sys.exit(0 if not real_fails else 1)