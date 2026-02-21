"""
test_transformation.py
======================
Integration + accuracy test for the entire transformation module.

Run from your project root (where this file lives alongside the .py rule files):

    # plain Python (no pytest needed):
    python test_transformation.py

    # or with pytest for CI:
    python -m pytest test_transformation.py -v

What this covers
----------------
1.  Scaffold integrity         — all Angular workspace files created
2.  ControllerToComponent      — .ts / .html / routing entries written
3.  ServiceToInjectable        — @Injectable() file written correctly
4.  HttpToHttpClient           — HttpClientModule patched, method injected
5.  SimpleWatchToRxjs          — BehaviorSubject injected into component
6.  RuleApplier (full run)     — orchestrates all rules, correct total changes
7.  Idempotency                — running the pipeline twice is safe
8.  Fallback name heuristic    — rules fire even when patterns are EMPTY
9.  Empty input edge case      — no rule crashes on totally empty data

Accuracy score = (passed individual checks) / (total checks) × 100 %
"""

import sys
import traceback
import tempfile
import types
import importlib.util
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum, auto

# ─────────────────────────────────────────────────────────────────────────────
# Minimal IR stubs — lets the test run WITHOUT the full pipeline installed.
# Delete this block and swap in your real imports if the project is on PYTHONPATH.
# ─────────────────────────────────────────────────────────────────────────────

class ChangeSource(Enum):
    RULE   = auto()
    MANUAL = auto()

@dataclass
class Change:
    before_id: str
    after_id:  str
    source:    ChangeSource
    reason:    str = ""

class SemanticRole(Enum):
    CONTROLLER       = auto()
    SERVICE          = auto()
    HTTP_CALL        = auto()
    SHALLOW_WATCH    = auto()
    TEMPLATE_BINDING = auto()

@dataclass
class ClassNode:
    id:   str
    name: str

@dataclass
class ModuleNode:
    path:    str
    classes: List[ClassNode] = field(default_factory=list)

@dataclass
class HttpCallNode:
    id:     str
    file:   str
    method: str
    url:    Optional[str] = None

@dataclass
class WatchNode:
    id:   str
    name: str

@dataclass
class AnalysisResult:
    modules:    List[ModuleNode]   = field(default_factory=list)
    http_calls: List[HttpCallNode] = field(default_factory=list)
    watches:    List[WatchNode]    = field(default_factory=list)

@dataclass
class PatternResult:
    roles_by_node:    Dict[str, List[SemanticRole]] = field(default_factory=dict)
    matched_patterns: List = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# Inject stubs into sys.modules so real rule files can import them
# ─────────────────────────────────────────────────────────────────────────────

def _stub(name, **attrs):
    m = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(m, k, v)
    sys.modules[name] = m
    return m

_stub("ir")
_stub("ir.migration_model")
_stub("ir.migration_model.change",  Change=Change)
_stub("ir.migration_model.base",    ChangeSource=ChangeSource)
_stub("pipeline")
_stub("pipeline.patterns")
_stub("pipeline.patterns.roles",    SemanticRole=SemanticRole)
_stub("pipeline.transformation")


# ─────────────────────────────────────────────────────────────────────────────
# Load real transformation files from disk
#
# ROOT_DIR = the folder that contains angular_project_scaffold.py, applier.py
#            and the rules/angularjs/ subfolder.
# Adjust ROOT_DIR if this test file lives somewhere else.
# ─────────────────────────────────────────────────────────────────────────────

ROOT_DIR = Path(__file__).parent

def _load(module_name: str, rel_path: str):
    full = ROOT_DIR / rel_path
    if not full.exists():
        raise FileNotFoundError(
            f"Could not find '{full}'.\n"
            f"  ROOT_DIR is set to: {ROOT_DIR}\n"
            f"  Adjust ROOT_DIR at the top of this test file if needed."
        )
    spec = importlib.util.spec_from_file_location(module_name, full)
    mod  = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod

scaffold_mod = _load("pipeline.transformation.angular_project_scaffold",
                     "angular_project_scaffold.py")
helpers_mod  = _load("pipeline.transformation.helpers",
                     "helpers.py")
applier_mod  = _load("pipeline.transformation.applier",
                     "applier.py")

# Re-expose the modules so rule files can import them by package path
_stub("pipeline.transformation.angular_project_scaffold",
      AngularProjectScaffold=scaffold_mod.AngularProjectScaffold)
_stub("pipeline.transformation.helpers",
      **{k: getattr(helpers_mod, k) for k in dir(helpers_mod) if not k.startswith("_")})

ctrl_mod  = _load("pipeline.transformation.rules.angularjs.controller_to_component",
                  "rules/angularjs/controller_to_component.py")
svc_mod   = _load("pipeline.transformation.rules.angularjs.service_to_injectable",
                  "rules/angularjs/service_to_injectable.py")
http_mod  = _load("pipeline.transformation.rules.angularjs.http_to_httpclient",
                  "rules/angularjs/http_to_httpclient.py")
watch_mod = _load("pipeline.transformation.rules.angularjs.simple_watch_to_rxjs",
                  "rules/angularjs/simple_watch_to_rxjs.py")

AngularProjectScaffold    = scaffold_mod.AngularProjectScaffold
RuleApplier               = applier_mod.RuleApplier
ControllerToComponentRule = ctrl_mod.ControllerToComponentRule
ServiceToInjectableRule   = svc_mod.ServiceToInjectableRule
HttpToHttpClientRule      = http_mod.HttpToHttpClientRule
SimpleWatchToRxjsRule     = watch_mod.SimpleWatchToRxjsRule


# ─────────────────────────────────────────────────────────────────────────────
# Test infrastructure
# ─────────────────────────────────────────────────────────────────────────────

class TestResult:
    def __init__(self, name: str):
        self.name   = name
        self.checks: List[tuple] = []   # (label, passed, detail)
        self.errors: List[str]   = []

    def check(self, label: str, condition: bool, detail: str = ""):
        self.checks.append((label, bool(condition), detail))

    def error(self, msg: str):
        self.errors.append(msg)

    @property
    def passed(self):
        return not self.errors and all(ok for _, ok, _ in self.checks)

    @property
    def score(self):
        if not self.checks:
            return 0.0
        return sum(1 for _, ok, _ in self.checks if ok) / len(self.checks)

    def print_summary(self):
        icon = "✅ PASS" if self.passed else "❌ FAIL"
        print(f"\n{icon}  [{self.name}]  accuracy={self.score*100:.0f}%")
        for label, ok, detail in self.checks:
            tick   = "  ✓" if ok else "  ✗"
            suffix = f"  ({detail})" if detail else ""
            print(f"{tick}  {label}{suffix}")
        for e in self.errors:
            print(f"  💥  {e}")


def _contains(path: Path, *fragments: str) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    return all(f in text for f in fragments)


# ─────────────────────────────────────────────────────────────────────────────
# Canonical fixtures — cover every rule in one realistic scenario
# ─────────────────────────────────────────────────────────────────────────────

def _analysis():
    return AnalysisResult(
        modules=[
            ModuleNode("src/user.controller.js", [
                ClassNode("cls_user_ctrl",    "UserController"),
                ClassNode("cls_product_ctrl", "ProductController"),
            ]),
            ModuleNode("src/auth.service.js", [
                ClassNode("cls_auth_svc", "AuthService"),
            ]),
        ],
        http_calls=[
            HttpCallNode("http_001", "user.controller.js",    "get",  "/api/users"),
            HttpCallNode("http_002", "product.controller.js", "post", "/api/products"),
        ],
        watches=[
            WatchNode("watch_001", "UserController"),
        ],
    )

def _patterns():
    return PatternResult(roles_by_node={
        "cls_user_ctrl":    [SemanticRole.CONTROLLER, SemanticRole.SHALLOW_WATCH],
        "cls_product_ctrl": [SemanticRole.CONTROLLER],
        "cls_auth_svc":     [SemanticRole.SERVICE],
        "http_001":         [SemanticRole.HTTP_CALL],
        "http_002":         [SemanticRole.HTTP_CALL],
        "watch_001":        [SemanticRole.SHALLOW_WATCH],
    })


# ─────────────────────────────────────────────────────────────────────────────
# Test functions
# ─────────────────────────────────────────────────────────────────────────────

def test_scaffold(out_dir: str) -> TestResult:
    r = TestResult("1. Scaffold integrity")
    try:
        AngularProjectScaffold(out_dir).ensure()
        root = Path(out_dir)
        for rel in [
            "angular.json", "package.json", "tsconfig.json", "tsconfig.app.json",
            "src/main.ts", "src/index.html",
            "src/app/app.component.ts", "src/app/app.module.ts",
            "src/app/app-routing.module.ts",
        ]:
            r.check(f"exists: {rel}", (root / rel).exists())

        r.check("app.module.ts has BrowserModule",
                _contains(root / "src/app/app.module.ts", "BrowserModule"))
        r.check("main.ts bootstraps AppModule",
                _contains(root / "src/main.ts", "bootstrapModule(AppModule)"))
        r.check("routing module has Routes array",
                _contains(root / "src/app/app-routing.module.ts", "const routes: Routes"))
    except Exception:
        r.error(traceback.format_exc())
    return r


def test_controller_rule(out_dir: str) -> TestResult:
    r = TestResult("2. ControllerToComponent")
    try:
        changes = ControllerToComponentRule(out_dir).apply(_analysis(), _patterns())
        app     = Path(out_dir) / "src" / "app"
        routing = app / "app-routing.module.ts"

        # Files
        r.check("user.component.ts created",       (app / "user.component.ts").exists())
        r.check("user.component.html created",     (app / "user.component.html").exists())
        r.check("product.component.ts created",    (app / "product.component.ts").exists())
        r.check("product.component.html created",  (app / "product.component.html").exists())

        # TypeScript content
        r.check("@Component decorator present",    _contains(app / "user.component.ts", "@Component"))
        r.check("selector: 'app-user' present",    _contains(app / "user.component.ts", "selector: 'app-user'"))
        r.check("export class UserComponent",      _contains(app / "user.component.ts", "export class UserComponent"))

        # Routing
        r.check("routing imports UserComponent",   _contains(routing, "UserComponent"))
        r.check("routing imports ProductComponent",_contains(routing, "ProductComponent"))
        r.check("route /user registered",          _contains(routing, "path: 'user'"))
        r.check("route /product registered",       _contains(routing, "path: 'product'"))

        # Change records
        real = [c for c in changes if "debug" not in c.before_id]
        r.check("≥2 real Change records emitted",  len(real) >= 2, f"got {len(real)}")
        r.check("change references component_cls_user_ctrl",
                any("component_cls_user_ctrl" in c.after_id for c in changes))
    except Exception:
        r.error(traceback.format_exc())
    return r


def test_service_rule(out_dir: str) -> TestResult:
    r = TestResult("3. ServiceToInjectable")
    try:
        changes = ServiceToInjectableRule(out_dir).apply(_analysis(), _patterns())
        app     = Path(out_dir) / "src" / "app"

        service_files = list(app.glob("*service*.ts"))
        r.check("≥1 .service.ts file created",
                len(service_files) >= 1, f"found {[f.name for f in service_files]}")

        if service_files:
            sf = service_files[0]
            r.check("@Injectable present",            _contains(sf, "@Injectable"))
            r.check("providedIn: 'root' present",     _contains(sf, "providedIn: 'root'"))
            r.check("imports from @angular/core",     _contains(sf, "from '@angular/core'"))

        r.check("≥1 Change record emitted",           len(changes) >= 1, f"got {len(changes)}")
        r.check("after_id has 'injectable_' prefix",
                any(c.after_id.startswith("injectable_") for c in changes))
    except Exception:
        r.error(traceback.format_exc())
    return r


def test_http_rule(out_dir: str) -> TestResult:
    r = TestResult("4. HttpToHttpClient")
    try:
        changes  = HttpToHttpClientRule(out_dir).apply(_analysis(), _patterns())
        app      = Path(out_dir) / "src" / "app"
        mod_file = app / "app.module.ts"

        r.check("HttpClientModule added to app.module.ts",  _contains(mod_file, "HttpClientModule"))
        r.check("HttpClientModule import line present",      _contains(mod_file, "from '@angular/common/http'"))
        r.check("user.component.ts exists",                 (app / "user.component.ts").exists())

        comp = app / "user.component.ts"
        if comp.exists():
            r.check("load_get() method injected",    _contains(comp, "load_get"))
            r.check("HttpClient referenced",         _contains(comp, "HttpClient"))

        r.check("≥2 Change records emitted",         len(changes) >= 2, f"got {len(changes)}")
        r.check("after_id references httpclient",
                any("httpclient" in c.after_id for c in changes))
    except Exception:
        r.error(traceback.format_exc())
    return r


def test_watch_rule(out_dir: str) -> TestResult:
    r = TestResult("5. SimpleWatchToRxjs")
    try:
        changes = SimpleWatchToRxjsRule(out_dir).apply(_analysis(), _patterns())
        r.check("≥1 Change record emitted",       len(changes) >= 1, f"got {len(changes)}")
        r.check("after_id has 'rx_' prefix",
                any(c.after_id.startswith("rx_") for c in changes))

        app  = Path(out_dir) / "src" / "app"
        comp = app / "user.component.ts"
        if comp.exists():
            r.check("BehaviorSubject injected into user.component.ts",
                    _contains(comp, "BehaviorSubject"))
    except Exception:
        r.error(traceback.format_exc())
    return r


def test_rule_applier(out_dir: str) -> TestResult:
    r = TestResult("6. RuleApplier full pipeline")
    try:
        rules = [
            ControllerToComponentRule(out_dir),
            ServiceToInjectableRule(out_dir),
            HttpToHttpClientRule(out_dir),
            SimpleWatchToRxjsRule(out_dir),
        ]
        changes = RuleApplier(rules).apply_all(_analysis(), _patterns())
        real    = [c for c in changes if "debug" not in c.before_id and "canary" not in c.before_id]

        r.check("returns a list",                  isinstance(changes, list))
        r.check("total ≥5 real changes",           len(real) >= 5, f"got {len(real)}")
        r.check("all changes have RULE source",    all(c.source == ChangeSource.RULE for c in real))
        r.check("controller changes present",      any("component_" in c.after_id for c in real))
        r.check("injectable changes present",      any(c.after_id.startswith("injectable_") for c in real))
        r.check("httpclient changes present",      any("httpclient" in c.after_id for c in real))
        r.check("rxjs changes present",            any(c.after_id.startswith("rx_") for c in real))
    except Exception:
        r.error(traceback.format_exc())
    return r


def test_idempotency(out_dir: str) -> TestResult:
    r = TestResult("7. Idempotency (run twice, no corruption)")
    try:
        def _run():
            rules = [
                ControllerToComponentRule(out_dir),
                ServiceToInjectableRule(out_dir),
                HttpToHttpClientRule(out_dir),
                SimpleWatchToRxjsRule(out_dir),
            ]
            return RuleApplier(rules).apply_all(_analysis(), _patterns())

        changes_1 = _run()
        changes_2 = _run()   # must not crash

        r.check("first run returns changes",    len(changes_1) >= 1)
        r.check("second run does not crash",    True)

        app = Path(out_dir) / "src" / "app"
        for ts in app.glob("*.ts"):
            lines   = ts.read_text(encoding="utf-8").splitlines()
            imports = [l for l in lines if l.strip().startswith("import")]
            dupes   = len(imports) - len(set(imports))
            r.check(f"no duplicate imports in {ts.name}",
                    dupes == 0, f"{dupes} duplicate(s)" if dupes else "")

        r.check("routing module still valid after 2nd run",
                _contains(app / "app-routing.module.ts", "Routes"))
    except Exception:
        r.error(traceback.format_exc())
    return r


def test_fallback_name_heuristic(out_dir: str) -> TestResult:
    """Rules must fire even when patterns.roles_by_node is completely empty."""
    r = TestResult("8. Fallback: name heuristic (empty patterns)")
    try:
        empty_patterns = PatternResult()  # no roles at all

        ctrl_changes = ControllerToComponentRule(out_dir).apply(_analysis(), empty_patterns)
        svc_changes  = ServiceToInjectableRule(out_dir).apply(_analysis(), empty_patterns)

        real_ctrl = [c for c in ctrl_changes if "debug" not in c.before_id]
        real_svc  = [c for c in svc_changes  if "debug" not in c.before_id]

        r.check("ControllerRule fires (≥2 controllers by name)",
                len(real_ctrl) >= 2, f"got {len(real_ctrl)}")
        r.check("ServiceRule fires (≥1 service by name)",
                len(real_svc)  >= 1, f"got {len(real_svc)}")

        app = Path(out_dir) / "src" / "app"
        r.check("user.component.ts written via name fallback",
                (app / "user.component.ts").exists())
    except Exception:
        r.error(traceback.format_exc())
    return r


def test_empty_input(out_dir: str) -> TestResult:
    """Completely empty analysis + patterns — no rule should crash."""
    r = TestResult("9. Edge case: empty analysis + patterns")
    try:
        changes = RuleApplier([
            ControllerToComponentRule(out_dir),
            ServiceToInjectableRule(out_dir),
            HttpToHttpClientRule(out_dir),
            SimpleWatchToRxjsRule(out_dir),
        ]).apply_all(AnalysisResult(), PatternResult())

        r.check("no exception raised", True)
        r.check("returns a list",      isinstance(changes, list))
    except Exception:
        r.error(traceback.format_exc())
    return r


# ─────────────────────────────────────────────────────────────────────────────
# Runner
# ─────────────────────────────────────────────────────────────────────────────

def run_all_tests():
    print("=" * 65)
    print("   TRANSFORMATION MODULE — INTEGRATION + ACCURACY TEST SUITE")
    print("=" * 65)

    tmp     = tempfile.mkdtemp(prefix="evua_transform_")
    out_dir = str(Path(tmp) / "angular-app")
    print(f"\n📁 Temp output: {out_dir}\n")

    suite = [
        lambda: test_scaffold(out_dir),
        lambda: test_controller_rule(out_dir),
        lambda: test_service_rule(out_dir),
        lambda: test_http_rule(out_dir),
        lambda: test_watch_rule(out_dir),
        lambda: test_rule_applier(out_dir),
        lambda: test_idempotency(out_dir),
        lambda: test_fallback_name_heuristic(str(Path(tmp) / "angular-app-fallback")),
        lambda: test_empty_input(str(Path(tmp) / "angular-app-empty")),
    ]

    results: List[TestResult] = []
    for fn in suite:
        try:
            result = fn()
        except Exception:
            result = TestResult("unknown")
            result.error(traceback.format_exc())
        results.append(result)
        result.print_summary()

    total_checks  = sum(len(r.checks) for r in results)
    passed_checks = sum(sum(1 for _, ok, _ in r.checks if ok) for r in results)
    passed_tests  = sum(1 for r in results if r.passed)
    accuracy      = (passed_checks / total_checks * 100) if total_checks else 0.0

    print("\n" + "=" * 65)
    print(f"  TEST GROUPS : {passed_tests}/{len(results)} passed")
    print(f"  CHECKS      : {passed_checks}/{total_checks} passed")
    print(f"  ACCURACY    : {accuracy:.1f}%")
    print("=" * 65)

    if accuracy == 100.0:
        print("\n🎉  Transformation module is fully functional!\n")
    elif accuracy >= 80.0:
        print("\n⚠️   Mostly working — fix the ✗ items above.\n")
    else:
        print("\n❌  Significant issues detected — review ✗ items above.\n")

    print(f"📁 Inspect generated files at:\n   {out_dir}\n")
    return accuracy


# ─────────────────────────────────────────────────────────────────────────────
# pytest entry points (used when running: python -m pytest test_transformation.py)
# ─────────────────────────────────────────────────────────────────────────────

import pytest

@pytest.fixture(scope="module")
def shared_out(tmp_path_factory):
    return str(tmp_path_factory.mktemp("angular-app"))

def _assert(result: TestResult):
    fails = [f"  ✗  {l}" for l, ok, _ in result.checks if not ok]
    if result.errors:
        fails += [f"  💥  {e}" for e in result.errors]
    assert not fails, "\n" + "\n".join(fails)

def test_pytest_scaffold(shared_out):          _assert(test_scaffold(shared_out))
def test_pytest_controller(shared_out):        _assert(test_controller_rule(shared_out))
def test_pytest_service(shared_out):           _assert(test_service_rule(shared_out))
def test_pytest_http(shared_out):              _assert(test_http_rule(shared_out))
def test_pytest_watch(shared_out):             _assert(test_watch_rule(shared_out))
def test_pytest_applier(shared_out):           _assert(test_rule_applier(shared_out))
def test_pytest_idempotency(shared_out):       _assert(test_idempotency(shared_out))
def test_pytest_name_heuristic(tmp_path):
    _assert(test_fallback_name_heuristic(str(tmp_path / "fb")))
def test_pytest_empty_input(tmp_path):
    _assert(test_empty_input(str(tmp_path / "empty")))


if __name__ == "__main__":
    accuracy = run_all_tests()
    sys.exit(0 if accuracy >= 80.0 else 1)
