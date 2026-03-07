"""
bench-10-service-methods — extended assertion suite
===================================================

Validates full HTTP migration behavior including:

• dynamic URLs
• request bodies
• config-object $http syntax
• multi-call methods
• promise → RxJS conversion
• DI preservation
• lifecycle conversion
"""

import sys
from pathlib import Path
import tempfile


# ─────────────────────────────────────────────
# Locate Angular output
# ─────────────────────────────────────────────
def find_app_dir():
    root = Path(__file__).resolve().parent
    candidates = []

    def add(p):
        if p.exists():
            candidates.append((p.stat().st_mtime, p))

    add(root / "out/angular-app/src/app")
    add(root / "out/angular-app/angular-app/src/app")

    out = root / "out"
    if out.exists():
        for d in out.iterdir():
            if d.name.startswith(".tmp_"):
                add(d / "angular-app/src/app")

    tmp = Path(tempfile.gettempdir())
    for d in tmp.glob("evua_shadow_*"):
        add(d / "angular-app/src/app")

    if not candidates:
        raise RuntimeError("Angular output not found")

    candidates.sort(reverse=True)
    return candidates[0][1]


OUT = find_app_dir()

print("Reading:", OUT)
print()


PASS, FAIL = [], []


def check(name, cond):
    if cond:
        PASS.append(name)
        print(" PASS", name)
    else:
        FAIL.append(name)
        print(" FAIL", name)


# ─────────────────────────────────────────────
# Load service
# ─────────────────────────────────────────────
svc = (OUT / "notificationservice.service.ts").read_text()

dash = (OUT / "dashboard.component.ts").read_text()
settings = (OUT / "settings.component.ts").read_text()


# ─────────────────────────────────────────────
# 1. Service methods preserved
# ─────────────────────────────────────────────
check("getAll() preserved", "getAll()" in svc)
check("markRead() preserved", "markRead(" in svc)
check("clear() preserved", "clear()" in svc)


# ─────────────────────────────────────────────
# 2. No invented methods
# ─────────────────────────────────────────────
check("no fetchNotifications", "fetchNotifications" not in svc)
check("no putNotifications", "putNotifications" not in svc)


# ─────────────────────────────────────────────
# 3. Dynamic URL preserved
# ─────────────────────────────────────────────
check(
    "dynamic URL preserved",
    "/api/notifications/" in svc and "${id}" in svc
)


# ─────────────────────────────────────────────
# 4. HTTP request body preserved
# ─────────────────────────────────────────────
check(
    "request body preserved",
    "{ read: true }" in svc
)


# ─────────────────────────────────────────────
# 5. Observable pipeline exists
# ─────────────────────────────────────────────
check(
    "RxJS pipe used",
    ".pipe(" in svc
)


# ─────────────────────────────────────────────
# 6. catchError conversion
# ─────────────────────────────────────────────
check(
    "catchError present",
    "catchError" in svc
)


# ─────────────────────────────────────────────
# 7. No $scope anywhere
# ─────────────────────────────────────────────
check(
    "no $scope in service",
    "$scope" not in svc
)

check(
    "no $scope in dashboard",
    "$scope" not in dash
)

check(
    "no $scope in settings",
    "$scope" not in settings
)


# ─────────────────────────────────────────────
# 8. Controller lifecycle conversion
# ─────────────────────────────────────────────
check(
    "Dashboard OnInit created",
    "implements OnInit" in dash
)

check(
    "ngOnInit exists",
    "ngOnInit()" in dash
)

check(
    "loadDashboard called in ngOnInit",
    "this.loadDashboard()" in dash
)


# ─────────────────────────────────────────────
# 9. No false ngOnInit
# ─────────────────────────────────────────────
check(
    "SettingsController no ngOnInit",
    "ngOnInit" not in settings
)


# ─────────────────────────────────────────────
# 10. Angular HttpClient used
# ─────────────────────────────────────────────
check(
    "HttpClient used",
    "HttpClient" in svc
)


# ─────────────────────────────────────────────
# Results
# ─────────────────────────────────────────────
print()
print("Results:", len(PASS), "passed,", len(FAIL), "failed")

if FAIL:
    print("FAILED:", FAIL)
    sys.exit(1)
else:
    print("ALL ASSERTIONS PASSED")