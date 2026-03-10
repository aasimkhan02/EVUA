"""
bench-ai-assertions.py
=======================

Structural + compilation assertions for AI-assisted output.

Unlike bench-100-assertions.py (which tests deterministic engine output),
this suite tests the AI-completed files. There is no ground truth for
correctness, so assertions test STRUCTURE and COMPILABILITY only.

Run after:
    python cli.py benchmarks/angularjs/bench-100-full-migration --ai-assist

Then:
    python benchmarks/angularjs/bench-100-full-migration/bench-ai-assertions.py

Sections
--------
A  — Pipe bodies completed (transform() is non-trivial)
B  — Stub templates completed (real HTML elements present)
C  — Link function migrated (ngAfterViewInit present)
D  — No AngularJS syntax leaked into AI output
E  — TypeScript compilation (tsc --noEmit)

Exit code 0 if all pass, 1 if any fail.
"""

import re
import subprocess
import sys
from pathlib import Path

# ── locate output dir ─────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).parent
ENGINE_ROOT = SCRIPT_DIR.parent.parent.parent   # project root (where cli.py lives)
APP_DIR     = ENGINE_ROOT / "out" / "angular-app" / "src" / "app"

if not APP_DIR.exists():
    print(f"[FATAL] App dir not found: {APP_DIR}")
    print("        Run:  python cli.py benchmarks/angularjs/bench-100-full-migration --ai-assist")
    sys.exit(1)

# ── assertion helpers ─────────────────────────────────────────────────────────

passed = 0
failed = 0
skipped = 0
failures = []


def ok(label: str):
    global passed
    passed += 1
    print(f"  PASS  {label}")


def fail(label: str, detail: str = ""):
    global failed
    failed += 1
    msg = f"  FAIL  {label}"
    if detail:
        msg += f"\n          {detail}"
    print(msg)
    failures.append(label)


def skip(label: str, reason: str = ""):
    global skipped
    skipped += 1
    print(f"  SKIP  {label}" + (f"  ({reason})" if reason else ""))


def section(title: str):
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def file_exists(path: Path, label: str) -> bool:
    if path.exists():
        return True
    skip(label, f"file not found: {path.name}")
    return False


# ── Section A: Pipe bodies ────────────────────────────────────────────────────

section("A — Pipe transform() body completion")

# bench-100 produces 3 pipes: currency-format, truncate, status-label
EXPECTED_PIPES = [
    ("currencyformat.pipe.ts", "currencyFormat"),
    ("truncate.pipe.ts",       "truncate"),
    ("capitalize.pipe.ts",     "capitalize"),
]

for fname, filter_name in EXPECTED_PIPES:
    pipe_file = APP_DIR / fname
    label_prefix = f"[{fname}]"

    if not file_exists(pipe_file, f"{label_prefix} file exists"):
        continue

    content = read(pipe_file)

    # A1: transform() must exist
    if "transform(" in content:
        ok(f"{label_prefix} has transform() method")
    else:
        fail(f"{label_prefix} has transform() method", "transform( not found in file")
        continue

    # A2: transform() must be non-trivial (not just `return value;` stub)
    # Extract the transform method body
    match = re.search(r'transform\s*\([^)]*\)\s*:\s*\w+\s*\{([^}]+)\}', content, re.DOTALL)
    if match:
        body = match.group(1).strip()
        if body == "return value;" or body == "return value":
            fail(f"{label_prefix} transform() is non-trivial (AI completed it)",
                 "transform() still returns `return value;` — AI did not complete it")
        else:
            ok(f"{label_prefix} transform() is non-trivial (AI completed it)")
    else:
        # Multi-line body — just check the stub marker isn't the only thing there
        if "return value;" in content and content.count("\n") < 20:
            fail(f"{label_prefix} transform() is non-trivial (AI completed it)",
                 "file still looks like a stub")
        else:
            ok(f"{label_prefix} transform() is non-trivial (AI completed it)")

    # A3: @Pipe decorator must still be present (AI didn't strip it)
    if "@Pipe(" in content:
        ok(f"{label_prefix} @Pipe decorator preserved")
    else:
        fail(f"{label_prefix} @Pipe decorator preserved", "@Pipe( not found — AI broke the structure")

    # A4: AI migration comment or no longer has the stub comment
    if "Original AngularJS filter body" not in content:
        ok(f"{label_prefix} original JS stub comment removed by AI")
    else:
        # It's acceptable if the AI kept the comment but also wrote an implementation
        # Only fail if transform() is still stub
        skip(f"{label_prefix} original JS stub comment removed by AI",
             "comment still present (acceptable if body is non-trivial)")


# ── Section B: Stub templates ─────────────────────────────────────────────────

section("B — Stub template completion")

# bench-100 has 6 controllers: auth, dashboard, userList, productCatalog, search, userDetail
# dashboard and userList had real AngularJS templates → should be SKIPPED by AI (already have content)
# auth, productCatalog, search, userDetail had NO templates → AI should complete them
AI_TEMPLATE_TARGETS = [
    "auth.component.html",
    "product.component.html",
    "search.component.html",
    "userdetail.component.html",
]
REAL_TEMPLATE_FILES = [
    "dashboard.component.html",
    "userlist.component.html",
]

for fname in AI_TEMPLATE_TARGETS:
    html_file = APP_DIR / fname
    label_prefix = f"[{fname}]"

    if not file_exists(html_file, f"{label_prefix} file exists"):
        continue

    content = read(html_file)

    # B1: stub marker must be gone (AI replaced it)
    if "TODO: no AngularJS template found" not in content:
        ok(f"{label_prefix} stub marker replaced by AI")
    else:
        fail(f"{label_prefix} stub marker replaced by AI",
             "TODO: no AngularJS template found still present — AI did not complete it")
        continue  # remaining assertions meaningless

    # B2: AI migration comment present (proves AI wrote this)
    if "AI-assisted migration" in content:
        ok(f"{label_prefix} has AI migration comment (traceable)")
    else:
        skip(f"{label_prefix} has AI migration comment (traceable)",
             "comment absent — acceptable if file was manually completed")

    # B3: at least one real HTML element (not just the stub h2)
    has_real_element = bool(re.search(r'<(div|form|input|button|p|h[1-6]|ul|li|span|table|select|textarea)\b',
                                      content, re.IGNORECASE))
    if has_real_element:
        ok(f"{label_prefix} contains real HTML elements")
    else:
        fail(f"{label_prefix} contains real HTML elements",
             "no recognizable HTML elements found")

    # B4: Angular syntax used (not AngularJS)
    has_angular_syntax = bool(re.search(r'\*ngIf|\*ngFor|\(click\)|\[ngModel\]|\[\(ngModel\)\]|\[disabled\]',
                                         content))
    if has_angular_syntax:
        ok(f"{label_prefix} uses Angular template syntax")
    else:
        skip(f"{label_prefix} uses Angular template syntax",
             "no Angular-specific syntax detected (may be static content)")

    # B5: no AngularJS syntax leaked in
    ng1_leak = re.search(r'ng-model|ng-repeat|ng-if|ng-show|ng-click|ng-bind|\{\{[^}]+\}\}',
                          content)
    if ng1_leak:
        fail(f"{label_prefix} no AngularJS syntax leaked in",
             f"found: {ng1_leak.group()}")
    else:
        ok(f"{label_prefix} no AngularJS syntax leaked in")


# B6: real templates should NOT have been modified (AI must skip them)
for fname in REAL_TEMPLATE_FILES:
    html_file = APP_DIR / fname
    if not html_file.exists():
        skip(f"[{fname}] AI skipped real template (file not found)")
        continue
    content = read(html_file)
    if "AI-assisted migration" in content:
        fail(f"[{fname}] AI correctly skipped real template (had content)",
             "AI-assist migration comment found — AI overwrote a file that had real content")
    else:
        ok(f"[{fname}] AI correctly skipped real template (had content)")


# ── Section C: Link function migration ────────────────────────────────────────

section("C — Link function → ngAfterViewInit() migration")

# bench-100: userCard directive has has_link=True
LINK_DIRECTIVE_COMPONENT = "usercard.component.ts"

link_file = APP_DIR / LINK_DIRECTIVE_COMPONENT

if not link_file.exists():
    skip(f"[{LINK_DIRECTIVE_COMPONENT}] file exists", "component not found")
else:
    content = read(link_file)

    # C1: ngAfterViewInit must be implemented
    if "ngAfterViewInit()" in content:
        ok(f"[{LINK_DIRECTIVE_COMPONENT}] ngAfterViewInit() implemented")
    else:
        fail(f"[{LINK_DIRECTIVE_COMPONENT}] ngAfterViewInit() implemented",
             "ngAfterViewInit() not found — AI did not migrate the link function")

    # C2: AfterViewInit interface declared
    if "AfterViewInit" in content:
        ok(f"[{LINK_DIRECTIVE_COMPONENT}] implements AfterViewInit")
    else:
        fail(f"[{LINK_DIRECTIVE_COMPONENT}] implements AfterViewInit",
             "AfterViewInit not in file")

    # C3: ElementRef injected (needed for DOM access)
    if "ElementRef" in content:
        ok(f"[{LINK_DIRECTIVE_COMPONENT}] ElementRef injected (DOM access)")
    else:
        fail(f"[{LINK_DIRECTIVE_COMPONENT}] ElementRef injected (DOM access)",
             "ElementRef not found — DOM manipulation has no reference")

    # C4: link stub comment must be gone or resolved
    if "port DOM logic to ngAfterViewInit" not in content:
        ok(f"[{LINK_DIRECTIVE_COMPONENT}] link() stub comment removed")
    else:
        fail(f"[{LINK_DIRECTIVE_COMPONENT}] link() stub comment removed",
             "TODO comment still present — AI did not migrate")

    # C5: @Component still intact
    if "@Component(" in content:
        ok(f"[{LINK_DIRECTIVE_COMPONENT}] @Component decorator preserved")
    else:
        fail(f"[{LINK_DIRECTIVE_COMPONENT}] @Component decorator preserved",
             "AI broke the @Component structure")


# ── Section D: No AngularJS syntax leaked ─────────────────────────────────────

section("D — No AngularJS syntax in any AI-completed file")

ALL_AI_FILES = (
    [APP_DIR / f for f in [
        "currencyformat.pipe.ts", "truncate.pipe.ts", "capitalize.pipe.ts",
        "auth.component.html", "product.component.html",
        "search.component.html", "userdetail.component.html",
        "usercard.component.ts",
    ]]
)

NG1_PATTERNS = [
    (r'\$scope',          "$scope reference"),
    (r'\$http\b',         "$http reference"),
    (r'\$routeProvider',  "$routeProvider reference"),
    (r'ng-model\b',       "ng-model attribute"),
    (r'ng-repeat\b',      "ng-repeat attribute"),
    (r'ng-if\b',          "ng-if attribute"),
    (r'ng-show\b',        "ng-show attribute"),
    (r'ng-click\b',       "ng-click attribute"),
    (r'\.controller\(',   ".controller() call"),
    (r'\.factory\(',      ".factory() call"),
    (r'\.directive\(',    ".directive() call"),
]

for ai_file in ALL_AI_FILES:
    if not ai_file.exists():
        skip(f"[{ai_file.name}] no AngularJS leaks", "file not found")
        continue
    content = read(ai_file)
    leaks = [(label, pat) for pat, label in NG1_PATTERNS
             if re.search(pat, content)]
    if leaks:
        fail(f"[{ai_file.name}] no AngularJS leaks",
             "leaked: " + ", ".join(l for l, _ in leaks))
    else:
        ok(f"[{ai_file.name}] no AngularJS leaks")


# ── Section E: TypeScript compilation ─────────────────────────────────────────

section("E — TypeScript compilation (tsc --noEmit)")

# Locate tsconfig.json in the generated project
TSC_ROOT = ENGINE_ROOT / "out" / "angular-app"
TSCONFIG = TSC_ROOT / "tsconfig.app.json"
if not TSCONFIG.exists():
    TSCONFIG = TSC_ROOT / "tsconfig.json"

if not TSCONFIG.exists():
    skip("tsc --noEmit passes on generated project", f"tsconfig not found in {TSC_ROOT}")
else:
    # Check if tsc is available
    import sys as _sys
    tsc_bin = "tsc.cmd" if _sys.platform == "win32" else "tsc"
    tsc_check = subprocess.run(
        [tsc_bin, "--version"],
        capture_output=True, text=True
    )
    if tsc_check.returncode != 0:
        skip("tsc --noEmit passes on generated project",
             "tsc not found — install Node.js + TypeScript: npm install -g typescript")
    else:
        tsc_version = tsc_check.stdout.strip()
        print(f"  Using: {tsc_version}")
        result_tsc = subprocess.run(
            [tsc_bin, "--noEmit", "--project", str(TSCONFIG)],
            capture_output=True, text=True, cwd=str(TSC_ROOT)
        )
        if result_tsc.returncode == 0:
            ok("tsc --noEmit passes on generated project")
        else:
            # Count error lines for the summary
            error_lines = [l for l in result_tsc.stdout.splitlines() if "error TS" in l]
            n_errors = len(error_lines)
            fail("tsc --noEmit passes on generated project",
                 f"{n_errors} TypeScript error(s). First 5:\n" +
                 "\n          ".join(error_lines[:5]))
            # Print all errors for diagnosis
            print("\n  [tsc full output]")
            for line in result_tsc.stdout.splitlines()[:30]:
                print(f"    {line}")
            if len(result_tsc.stdout.splitlines()) > 30:
                print(f"    ... ({len(result_tsc.stdout.splitlines()) - 30} more lines)")


# ── Final summary ─────────────────────────────────────────────────────────────

total = passed + failed + skipped
print(f"\n{'═' * 60}")
print(f"  bench-ai-assertions  |  {total} total")
print(f"  PASSED:  {passed:3d}   FAILED: {failed:3d}   SKIPPED: {skipped:3d}")
print(f"{'═' * 60}")

if failed == 0 and passed > 0:
    print("\n  ✓  All AI-assist assertions passed.")
    print("     AI integration is working. Ready for tsc validation.\n")
elif failed == 0 and passed == 0:
    print("\n  ⚠  All assertions skipped — run --ai-assist first.\n")
    print("     python cli.py benchmarks/angularjs/bench-100-full-migration --ai-assist\n")
else:
    print(f"\n  ✗  {failed} assertion(s) failed:\n")
    for f_label in failures:
        print(f"     - {f_label}")
    print()

sys.exit(0 if failed == 0 else 1)