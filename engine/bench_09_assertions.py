"""
bench-09-merge-strict  --  assertion suite
==========================================
Drop this file in the engine root.
Run AFTER: python cli.py benchmarks/angularjs/bench-09-merge-strict

Works for both --diff (AppData shadow) and normal (out/.tmp_*) runs.
"""

import sys
from pathlib import Path


def _find_app_dir() -> Path:
    engine_root = Path(__file__).resolve().parent
    out = engine_root / "out"

    if not out.exists():
        raise FileNotFoundError("engine/out directory not found")

    # 1️⃣ legacy committed
    p = out / "angular-app" / "src" / "app"
    if p.exists():
        return p

    # 2️⃣ nested scaffold (your current output)
    p = out / "angular-app" / "angular-app" / "src" / "app"
    if p.exists():
        return p

    # 3️⃣ temp runs
    candidates = list(out.glob(".tmp_*/angular-app/src/app"))
    if candidates:
        candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return candidates[0]

    raise FileNotFoundError(
        "Cannot find angular-app output.\n"
        "Run first: python cli.py benchmarks/angularjs/bench-09-merge-strict"
    )


def scope_in_code(text: str) -> bool:
    """
    True only if $scope appears in executable code — not in comment lines.
    Skips lines whose first non-whitespace characters are //.
    """
    for line in text.splitlines():
        if line.strip().startswith("//"):
            continue
        if "$scope" in line:
            return True
    return False


# ── Locate output ─────────────────────────────────────────────────────────
try:
    OUT = _find_app_dir()
except FileNotFoundError as e:
    print(f"ERROR: {e}")
    sys.exit(1)

print(f"Reading output from: {OUT}\n")

PASS, FAIL = [], []


def check(name: str, cond: bool, detail: str = ""):
    if cond:
        PASS.append(name)
        print(f"  PASS  {name}")
    else:
        FAIL.append(name)
        print(f"  FAIL  {name}" + (f"  ({detail})" if detail else ""))


# ── 1. $scope eliminated from executable code ─────────────────────────────
for fname in ["admin.component.ts", "order.component.ts",
              "settings.component.ts", "search.component.ts"]:
    txt = (OUT / fname).read_text(encoding="utf-8")
    check(f"no $scope in code: {fname}",
          not scope_in_code(txt),
          "literal $scope found outside comment lines")

# ── 2. Correct this.x = res assignments ──────────────────────────────────
admin = (OUT / "admin.component.ts").read_text(encoding="utf-8")
check("this.users = res in admin.load()",  "this.users = res" in admin)
check("this.roles = res in admin.load()",  "this.roles = res" in admin)

order = (OUT / "order.component.ts").read_text(encoding="utf-8")
check("this.lastOrder = res in order",     "this.lastOrder = res" in order)

# ── 3. res.data eliminated everywhere ────────────────────────────────────
for fname in ["admin.component.ts", "order.component.ts",
              "settings.component.ts", "search.component.ts"]:
    txt = (OUT / fname).read_text(encoding="utf-8")
    check(f"no res.data in {fname}", "res.data" not in txt)

# ── 4. Request body sanitized: $scope.cart → this.cart ───────────────────
check("no $scope.cart in placeOrder request body",
      "$scope.cart" not in order,
      "found '$scope.cart' — req_body sanitizer not applied")
check("this.cart present in placeOrder request body", "this.cart" in order)

# ── 5. Dynamic URL preserved ──────────────────────────────────────────────
check("loadOrder URL not collapsed to '/'",
      "this.http.get('/')" not in order,
      "dynamic URL '/api/orders/' + id collapsed to '/'")
check("/api/orders/ fragment in loadOrder", "/api/orders/" in order)

# ── 6. Dedup: both GET and POST /api/users survive ────────────────────────
user_svc = (OUT / "user.service.ts").read_text(encoding="utf-8")
has_get  = "get('/api/users')"  in user_svc
has_post = "post('/api/users'" in user_svc
check("UserService GET /api/users present",  has_get)
check("UserService POST /api/users present", has_post)
check("dedup kept both GET and POST /api/users",
      has_get and has_post, f"GET={has_get} POST={has_post}")

# ── 7. catchError in SearchComponent ─────────────────────────────────────
search = (OUT / "search.component.ts").read_text(encoding="utf-8")
check("SearchComponent has catchError pipe", "catchError" in search)
check("this.results = res in search",        "this.results = res" in search)

# ── Summary ───────────────────────────────────────────────────────────────
print()
print(f"Results: {len(PASS)} passed, {len(FAIL)} failed")
if FAIL:
    print("FAILED:", FAIL)
    sys.exit(1)
else:
    print("ALL ASSERTIONS PASSED")