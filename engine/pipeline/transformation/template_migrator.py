"""
AngularJS → Angular template migrator.

Two entry points:

  migrate_template(html)
      Full-file rewrite. All ng-* attributes replaced in-place.
      Used when a template file is already per-component.

  extract_controller_template(html, controller_name)
      Finds the outermost element with ng-controller="ControllerName",
      extracts its innerHTML, and migrates it.
      Used when all controllers share a single index.html file
      (the most common real-world AngularJS layout).

Deterministic rewrites:
  ng-repeat="item in items"      → *ngFor="let item of items"
  ng-if="expr"                   → *ngIf="expr"
  ng-show="expr"                 → *ngIf="expr"    <!-- migrated from ng-show -->
  ng-hide="expr"                 → *ngIf="!(expr)" <!-- migrated from ng-hide -->
  ng-class="expr"                → [ngClass]="expr"
  ng-style="expr"                → [ngStyle]="expr"
  ng-model="x"                   → [(ngModel)]="x"
  ng-click="fn()"                → (click)="fn()"
  ng-submit="fn()"               → (submit)="fn()"
  ng-change="fn()"               → (change)="fn()"
  ng-blur="fn()"                 → (blur)="fn()"
  ng-focus="fn()"                → (focus)="fn()"
  ng-keyup="fn()"                → (keyup)="fn()"
  ng-keydown="fn()"              → (keydown)="fn()"
  ng-href="url"                  → [href]="url"
  ng-src="url"                   → [src]="url"
  ng-disabled="expr"             → [disabled]="expr"
  ng-readonly="expr"             → [readOnly]="expr"
  ng-checked="expr"              → [checked]="expr"
  ng-value="expr"                → [value]="expr"
  ng-placeholder="val"           → [placeholder]="val"
  ng-controller="..."            → removed
  ng-app="..."                   → removed

Filter → Pipe migrations (inside {{ }} expressions):
  {{ x | date:'short' }}         → {{ x | date:'short' }}   (compatible)
  {{ x | currency }}             → {{ x | currency }}       (compatible)
  {{ x | number }}               → {{ x | number }}         (compatible)
  {{ x | uppercase }}            → {{ x | uppercase }}      (compatible)
  {{ x | lowercase }}            → {{ x | lowercase }}      (compatible)
  {{ x | json }}                 → {{ x | json }}           (compatible)
  {{ x | limitTo:n }}            → {{ x | slice:0:n }}      (rewritten)
  {{ x | orderBy:'field' }}      → TODO (no direct Angular pipe)
  {{ x | filter:query }}         → TODO (use component logic)
  {{ x | customFilter }}         → TODO (create Angular pipe)

Non-deterministic patterns flagged with TODO comments.
"""

import re
from typing import Optional


# ---------------------------------------------------------------------------
# Attribute rewrite table
# ---------------------------------------------------------------------------

def _make_rewrite(ng_attr: str, angular_attr: str, quote: str = '"') -> tuple:
    """Build a (pattern, replacement) pair for a simple attribute rename."""
    q = re.escape(quote)
    other_q = "'" if quote == '"' else '"'
    pat = re.compile(rf'\b{re.escape(ng_attr)}\s*=\s*{q}([^{q}]+){q}', re.IGNORECASE)
    repl = lambda m, a=angular_attr, oq=quote: f'{a}={oq}{m.group(1)}{oq}'
    return (pat, repl)


_ATTRIBUTE_REWRITES = [
    # ── Structural ─────────────────────────────────────────────────────────
    (
        re.compile(r'\bng-repeat\s*=\s*"([^"]+)"', re.IGNORECASE),
        lambda m: f'*ngFor="let {_rewrite_ng_repeat(m.group(1))}"'
    ),
    (
        re.compile(r"\bng-repeat\s*=\s*'([^']+)'", re.IGNORECASE),
        lambda m: f"*ngFor=\"let {_rewrite_ng_repeat(m.group(1))}\""
    ),
    (re.compile(r'\bng-if\s*=\s*"([^"]+)"',  re.IGNORECASE), lambda m: f'*ngIf="{m.group(1)}"'),
    (re.compile(r"\bng-if\s*=\s*'([^']+)'",  re.IGNORECASE), lambda m: f"*ngIf=\"{m.group(1)}\""),
    (re.compile(r'\bng-show\s*=\s*"([^"]+)"', re.IGNORECASE), lambda m: f'*ngIf="{m.group(1)}" <!-- migrated from ng-show -->'),
    (re.compile(r"\bng-show\s*=\s*'([^']+)'", re.IGNORECASE), lambda m: f"*ngIf=\"{m.group(1)}\" <!-- migrated from ng-show -->"),
    (re.compile(r'\bng-hide\s*=\s*"([^"]+)"', re.IGNORECASE), lambda m: f'*ngIf="!({m.group(1)})" <!-- migrated from ng-hide -->'),
    (re.compile(r"\bng-hide\s*=\s*'([^']+)'", re.IGNORECASE), lambda m: f"*ngIf=\"!({m.group(1)})\" <!-- migrated from ng-hide -->"),

    # ── Property bindings ─────────────────────────────────────────────────
    (re.compile(r'\bng-class\s*=\s*"([^"]+)"',       re.IGNORECASE), lambda m: f'[ngClass]="{m.group(1)}"'),
    (re.compile(r"\bng-class\s*=\s*'([^']+)'",       re.IGNORECASE), lambda m: f"[ngClass]=\"{m.group(1)}\""),
    (re.compile(r'\bng-style\s*=\s*"([^"]+)"',       re.IGNORECASE), lambda m: f'[ngStyle]="{m.group(1)}"'),
    (re.compile(r"\bng-style\s*=\s*'([^']+)'",       re.IGNORECASE), lambda m: f"[ngStyle]=\"{m.group(1)}\""),
    (re.compile(r'\bng-disabled\s*=\s*"([^"]+)"',    re.IGNORECASE), lambda m: f'[disabled]="{m.group(1)}"'),
    (re.compile(r"\bng-disabled\s*=\s*'([^']+)'",    re.IGNORECASE), lambda m: f"[disabled]=\"{m.group(1)}\""),
    (re.compile(r'\bng-readonly\s*=\s*"([^"]+)"',    re.IGNORECASE), lambda m: f'[readOnly]="{m.group(1)}"'),
    (re.compile(r"\bng-readonly\s*=\s*'([^']+)'",    re.IGNORECASE), lambda m: f"[readOnly]=\"{m.group(1)}\""),
    (re.compile(r'\bng-checked\s*=\s*"([^"]+)"',     re.IGNORECASE), lambda m: f'[checked]="{m.group(1)}"'),
    (re.compile(r"\bng-checked\s*=\s*'([^']+)'",     re.IGNORECASE), lambda m: f"[checked]=\"{m.group(1)}\""),
    (re.compile(r'\bng-href\s*=\s*"([^"]+)"',        re.IGNORECASE), lambda m: f'[href]="{m.group(1)}"'),
    (re.compile(r"\bng-href\s*=\s*'([^']+)'",        re.IGNORECASE), lambda m: f"[href]=\"{m.group(1)}\""),
    (re.compile(r'\bng-src\s*=\s*"([^"]+)"',         re.IGNORECASE), lambda m: f'[src]="{m.group(1)}"'),
    (re.compile(r"\bng-src\s*=\s*'([^']+)'",         re.IGNORECASE), lambda m: f"[src]=\"{m.group(1)}\""),
    (re.compile(r'\bng-value\s*=\s*"([^"]+)"',       re.IGNORECASE), lambda m: f'[value]="{m.group(1)}"'),
    (re.compile(r"\bng-value\s*=\s*'([^']+)'",       re.IGNORECASE), lambda m: f"[value]=\"{m.group(1)}\""),
    (re.compile(r'\bng-placeholder\s*=\s*"([^"]+)"', re.IGNORECASE), lambda m: f'[placeholder]="{m.group(1)}"'),
    (re.compile(r"\bng-placeholder\s*=\s*'([^']+)'", re.IGNORECASE), lambda m: f"[placeholder]=\"{m.group(1)}\""),

    # ── Two-way binding ───────────────────────────────────────────────────
    (re.compile(r'\bng-model\s*=\s*"([^"]+)"',  re.IGNORECASE), lambda m: f'[(ngModel)]="{m.group(1)}"'),
    (re.compile(r"\bng-model\s*=\s*'([^']+)'",  re.IGNORECASE), lambda m: f"[(ngModel)]=\"{m.group(1)}\""),

    # ── Event bindings ────────────────────────────────────────────────────
    (re.compile(r'\bng-click\s*=\s*"([^"]+)"',    re.IGNORECASE), lambda m: f'(click)="{m.group(1)}"'),
    (re.compile(r"\bng-click\s*=\s*'([^']+)'",    re.IGNORECASE), lambda m: f"(click)=\"{m.group(1)}\""),
    (re.compile(r'\bng-submit\s*=\s*"([^"]+)"',   re.IGNORECASE), lambda m: f'(submit)="{m.group(1)}"'),
    (re.compile(r"\bng-submit\s*=\s*'([^']+)'",   re.IGNORECASE), lambda m: f"(submit)=\"{m.group(1)}\""),
    (re.compile(r'\bng-change\s*=\s*"([^"]+)"',   re.IGNORECASE), lambda m: f'(change)="{m.group(1)}"'),
    (re.compile(r"\bng-change\s*=\s*'([^']+)'",   re.IGNORECASE), lambda m: f"(change)=\"{m.group(1)}\""),
    (re.compile(r'\bng-blur\s*=\s*"([^"]+)"',     re.IGNORECASE), lambda m: f'(blur)="{m.group(1)}"'),
    (re.compile(r"\bng-blur\s*=\s*'([^']+)'",     re.IGNORECASE), lambda m: f"(blur)=\"{m.group(1)}\""),
    (re.compile(r'\bng-focus\s*=\s*"([^"]+)"',    re.IGNORECASE), lambda m: f'(focus)="{m.group(1)}"'),
    (re.compile(r"\bng-focus\s*=\s*'([^']+)'",    re.IGNORECASE), lambda m: f"(focus)=\"{m.group(1)}\""),
    (re.compile(r'\bng-keyup\s*=\s*"([^"]+)"',    re.IGNORECASE), lambda m: f'(keyup)="{m.group(1)}"'),
    (re.compile(r"\bng-keyup\s*=\s*'([^']+)'",    re.IGNORECASE), lambda m: f"(keyup)=\"{m.group(1)}\""),
    (re.compile(r'\bng-keydown\s*=\s*"([^"]+)"',  re.IGNORECASE), lambda m: f'(keydown)="{m.group(1)}"'),
    (re.compile(r"\bng-keydown\s*=\s*'([^']+)'",  re.IGNORECASE), lambda m: f"(keydown)=\"{m.group(1)}\""),

    # ── Remove AngularJS bootstrapping attributes ─────────────────────────
    (re.compile(r'\s*ng-app\s*=\s*"[^"]*"',        re.IGNORECASE), lambda m: ''),
    (re.compile(r"\s*ng-app\s*=\s*'[^']*'",        re.IGNORECASE), lambda m: ''),
    (re.compile(r'\s*ng-app\b',                     re.IGNORECASE), lambda m: ''),
    (re.compile(r'\s*ng-controller\s*=\s*"[^"]*"', re.IGNORECASE), lambda m: ''),
    (re.compile(r"\s*ng-controller\s*=\s*'[^']*'", re.IGNORECASE), lambda m: ''),
]

# Patterns that are detected but NOT auto-migrated — prepend a TODO comment
_TODO_PATTERNS = [
    (re.compile(r'\bng-include\b',    re.IGNORECASE), "ng-include → extract to child @Component"),
    (re.compile(r'\bng-transclude\b', re.IGNORECASE), "ng-transclude → use <ng-content> in Angular"),
    (re.compile(r'\bng-switch\b',     re.IGNORECASE), "ng-switch → use [ngSwitch] / *ngSwitchCase"),
    (re.compile(r'\bng-options\b',    re.IGNORECASE), "ng-options → use *ngFor on <option> elements"),
    (re.compile(r'\bng-bind-html\b',  re.IGNORECASE), "ng-bind-html → use [innerHTML] with DomSanitizer"),
    (re.compile(r'\bng-bind\b',       re.IGNORECASE), "ng-bind → use {{ }} interpolation"),
]

# Filter → Pipe rewrites inside {{ }} interpolations
_FILTER_REWRITES = [
    # Compatible (same name, no change needed — but we annotate them as verified)
    # Incompatible — must rewrite
    (re.compile(r'\|\s*limitTo\s*:\s*(\S+)',       re.IGNORECASE), r'| slice:0:\1'),
    # Filters with no Angular equivalent — flag with TODO
    (re.compile(r'\|\s*orderBy\b',                 re.IGNORECASE), '<!-- TODO: orderBy has no Angular pipe — sort in component --> | '),
    (re.compile(r'\|\s*filter\b',                  re.IGNORECASE), '<!-- TODO: filter pipe — move filtering logic to component --> | '),
]

# AngularJS script tags to remove from migrated output
_ANGULARJS_SCRIPT_RE = re.compile(
    r'<script[^>]+angularjs[^>]*>\s*</script>\s*\n?',
    re.IGNORECASE
)
_APP_JS_SCRIPT_RE = re.compile(
    r'<script[^>]+src\s*=\s*["\']src/app\.js["\'][^>]*>\s*</script>\s*\n?',
    re.IGNORECASE
)


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------

def _rewrite_ng_repeat(expr: str) -> str:
    """
    Convert ng-repeat value to *ngFor value.

    'item in items'              → 'item of items'
    'item in items track by $id' → 'item of items; trackBy: $id'
    '(key, val) in obj'          → annotated TODO
    """
    expr = expr.strip()
    if expr.startswith("("):
        return f"{expr}  <!-- TODO: object iteration — use keyvalue pipe: (obj | keyvalue) -->"

    track_match = re.search(r'\s+track\s+by\s+(\S+)', expr, re.IGNORECASE)
    if track_match:
        track_expr = track_match.group(1)
        base       = re.sub(r'\s+track\s+by\s+\S+', '', expr, flags=re.IGNORECASE).strip()
        base       = base.replace(" in ", " of ", 1)
        return f"{base}; trackBy: {track_expr}"

    return expr.replace(" in ", " of ", 1)


def _migrate_filters(html: str) -> str:
    """Apply filter → pipe rewrites inside {{ }} interpolations."""
    def rewrite_interpolation(m: re.Match) -> str:
        inner = m.group(1)
        for pattern, replacement in _FILTER_REWRITES:
            inner = pattern.sub(replacement, inner)
        return "{{ " + inner.strip() + " }}"

    return re.sub(r'\{\{\s*(.*?)\s*\}\}', rewrite_interpolation, html, flags=re.DOTALL)


def _strip_angularjs_scripts(html: str) -> str:
    """Remove AngularJS CDN script tags and app.js references."""
    html = _ANGULARJS_SCRIPT_RE.sub('', html)
    html = _APP_JS_SCRIPT_RE.sub('', html)
    return html


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_controller_template(html: str, controller_name: str) -> Optional[str]:
    """
    Find the outermost element with ng-controller="<controller_name>" in a
    monolithic HTML file and return its inner HTML (already migrated).

    Handles both:
      ng-controller="UserController"
      ng-controller="UserController as vm"

    Returns None if the controller is not found in the HTML.

    Algorithm:
      1. Find the opening tag containing ng-controller="<name>"
      2. Walk forward tracking open/close tags to find the matching close tag
      3. Extract the innerHTML
      4. Run migrate_template() on it
    """
    # Match the controller name (allow "as vm" alias)
    pattern = re.compile(
        r'<(\w+)[^>]*\bng-controller\s*=\s*["\']' + re.escape(controller_name) + r'(?:\s+as\s+\w+)?["\'][^>]*>',
        re.IGNORECASE
    )
    m = pattern.search(html)
    if not m:
        return None

    tag_name    = m.group(1)
    open_start  = m.start()
    inner_start = m.end()

    # Walk forward to find the matching closing tag
    depth   = 1
    pos     = inner_start
    open_re  = re.compile(rf'<{tag_name}(?:\s|>)', re.IGNORECASE)
    close_re = re.compile(rf'</{tag_name}\s*>', re.IGNORECASE)

    while pos < len(html) and depth > 0:
        next_open  = open_re.search(html, pos)
        next_close = close_re.search(html, pos)

        if next_close is None:
            break  # malformed HTML

        if next_open and next_open.start() < next_close.start():
            depth += 1
            pos = next_open.end()
        else:
            depth -= 1
            if depth == 0:
                inner_html = html[inner_start:next_close.start()]
                return migrate_template(inner_html.strip())
            pos = next_close.end()

    return None


def migrate_template(html: str) -> str:
    """
    Apply all deterministic AngularJS → Angular rewrites to an HTML string.

    Safe to call on:
     - Full index.html files
     - Extracted controller fragments
     - Standalone template files
    """
    result = html

    # 1. Strip AngularJS script tags (irrelevant in Angular)
    result = _strip_angularjs_scripts(result)

    # 2. Apply attribute rewrites
    for pattern, replacement in _ATTRIBUTE_REWRITES:
        result = pattern.sub(replacement, result)

    # 3. Migrate filter pipes inside {{ }}
    result = _migrate_filters(result)

    # 4. Prepend TODO comments for non-deterministic patterns
    for pattern, todo_msg in _TODO_PATTERNS:
        if pattern.search(result):
            result = f"<!-- TODO: {todo_msg} -->\n" + result

    return result


def migrate_template_from_raw(raw_template) -> str:
    """
    Fallback: build a basic Angular template from a RawTemplate object
    when no source HTML is available.
    """
    if raw_template is None:
        return "<!-- TODO: No template source found — migrate manually -->\n"

    loops        = getattr(raw_template, "loops",        []) or []
    conditionals = getattr(raw_template, "conditionals", []) or []
    events       = getattr(raw_template, "events",       []) or []

    lines = ["<!-- Angular template — migrated from AngularJS (no source HTML found) -->"]

    if loops:
        lines.append("\n<!-- Loops (ng-repeat → *ngFor) -->")
        for expr in loops:
            migrated = _rewrite_ng_repeat(expr)
            lines.append(f'<div *ngFor="let {migrated}">{{{{ item | json }}}}</div>')

    if conditionals:
        lines.append("\n<!-- Conditionals (ng-if → *ngIf) -->")
        for expr in conditionals:
            lines.append(f'<div *ngIf="{expr}"><!-- content --></div>')

    if events:
        lines.append("\n<!-- Events (ng-click → (click)) -->")
        for expr in events:
            fn = expr.split("(")[0].strip()
            lines.append(f'<button (click)="{fn}()">{fn}</button>')

    if not loops and not conditionals and not events:
        lines.append("<!-- TODO: No template patterns detected — migrate manually -->")

    return "\n".join(lines) + "\n"