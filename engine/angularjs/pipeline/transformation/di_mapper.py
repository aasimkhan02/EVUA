"""
pipeline/transformation/di_mapper.py

Maps AngularJS DI tokens to their Angular equivalents.

Each entry is: angularjs_token → (angular_import, angular_type, constructor_param_name)

Tokens not in this table are treated as custom services — they get imported
from a sibling .service.ts file with a TODO comment.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class DIMapping:
    angular_import: Optional[str]   # e.g. "@angular/router"  (None = custom service)
    angular_type:   str             # e.g. "Router"
    param_name:     str             # e.g. "router"
    import_symbol:  str             # e.g. "Router"  (what goes in the import { } braces)


# AngularJS token → Angular equivalent
# Tokens starting with $ are AngularJS built-ins.
# Anything NOT in this table is assumed to be a custom service/factory.
KNOWN_DI: dict[str, DIMapping] = {
    # ── Scope / lifecycle ─────────────────────────────────────────────────
    "$scope": DIMapping(
        angular_import=None,
        angular_type="$scope removed — use component properties directly",
        param_name="",          # omitted from constructor
        import_symbol="",
    ),
    "$rootScope": DIMapping(
        angular_import=None,
        angular_type="$rootScope — consider RxJS Subject for cross-component events",
        param_name="",
        import_symbol="",
    ),

    # ── HTTP ──────────────────────────────────────────────────────────────
    "$http": DIMapping(
        angular_import="@angular/common/http",
        angular_type="HttpClient",
        param_name="http",
        import_symbol="HttpClient",
    ),
    "$resource": DIMapping(
        angular_import="@angular/common/http",
        angular_type="HttpClient",
        param_name="http",
        import_symbol="HttpClient",
    ),

    # ── Router / state ────────────────────────────────────────────────────
    "$state": DIMapping(
        angular_import="@angular/router",
        angular_type="Router",
        param_name="router",
        import_symbol="Router",
    ),
    "$location": DIMapping(
        angular_import="@angular/router",
        angular_type="Router",
        param_name="router",
        import_symbol="Router",
    ),
    "$stateParams": DIMapping(
        angular_import="@angular/router",
        angular_type="ActivatedRoute",
        param_name="route",
        import_symbol="ActivatedRoute",
    ),
    "$routeParams": DIMapping(
        angular_import="@angular/router",
        angular_type="ActivatedRoute",
        param_name="route",
        import_symbol="ActivatedRoute",
    ),

    # ── Promises / async ──────────────────────────────────────────────────
    "$q": DIMapping(
        angular_import=None,
        angular_type="$q removed — use RxJS Observables or native Promises",
        param_name="",
        import_symbol="",
    ),
    "$timeout": DIMapping(
        angular_import=None,
        angular_type="$timeout removed — use setTimeout() or RxJS timer()",
        param_name="",
        import_symbol="",
    ),
    "$interval": DIMapping(
        angular_import=None,
        angular_type="$interval removed — use RxJS interval()",
        param_name="",
        import_symbol="",
    ),

    # ── DOM / compile ─────────────────────────────────────────────────────
    "$compile": DIMapping(
        angular_import=None,
        angular_type="$compile removed — use Angular component composition",
        param_name="",
        import_symbol="",
    ),
    "$element": DIMapping(
        angular_import="@angular/core",
        angular_type="ElementRef",
        param_name="el",
        import_symbol="ElementRef",
    ),
    "$document": DIMapping(
        angular_import="@angular/common",
        angular_type="DOCUMENT",
        param_name="document",
        import_symbol="DOCUMENT",
    ),

    # ── i18n ─────────────────────────────────────────────────────────────
    "$translate": DIMapping(
        angular_import=None,
        angular_type="$translate — install @ngx-translate/core and inject TranslateService",
        param_name="",
        import_symbol="",
    ),

    # ── Modal / UI Bootstrap ──────────────────────────────────────────────
    "$uibModal": DIMapping(
        angular_import=None,
        angular_type="$uibModal — install ng-bootstrap and inject NgbModal",
        param_name="",
        import_symbol="",
    ),
    "$modal": DIMapping(
        angular_import=None,
        angular_type="$modal — install ng-bootstrap and inject NgbModal",
        param_name="",
        import_symbol="",
    ),

    # ── Filter ────────────────────────────────────────────────────────────
    "$filter": DIMapping(
        angular_import=None,
        angular_type="$filter — use Angular Pipes instead",
        param_name="",
        import_symbol="",
    ),

    # ── Log ───────────────────────────────────────────────────────────────
    "$log": DIMapping(
        angular_import=None,
        angular_type="$log removed — use console.log() directly",
        param_name="",
        import_symbol="",
    ),
}


def resolve_di_tokens(tokens: list[str]) -> "DIResolution":
    """
    Given a list of AngularJS DI tokens, return:
      - imports: list of (symbol, from_module) pairs for TypeScript imports
      - constructor_params: list of 'private x: Type' strings (omitting $scope etc.)
      - comments: inline migration notes for omitted tokens
      - custom_services: list of token names that are custom (not in KNOWN_DI)
    """
    imports:           list[tuple[str, str]] = []  # (symbol, module)
    constructor_params: list[str] = []
    comments:          list[str] = []
    custom_services:   list[str] = []

    seen_types: set[str] = set()  # deduplicate (e.g. two tokens → same Angular type)

    for token in tokens:
        mapping = KNOWN_DI.get(token)

        if mapping is None:
            # Custom service / factory — treat as injectable service
            custom_services.append(token)
            continue

        if mapping.param_name == "":
            # Token is omitted from constructor (e.g. $scope, $q)
            comments.append(mapping.angular_type)
            continue

        # Deduplicate: $state and $location both → Router, only add once
        if mapping.angular_type in seen_types:
            continue
        seen_types.add(mapping.angular_type)

        if mapping.angular_import and mapping.import_symbol:
            imports.append((mapping.import_symbol, mapping.angular_import))

        constructor_params.append(f"private {mapping.param_name}: {mapping.angular_type}")

    return DIResolution(
        imports=imports,
        constructor_params=constructor_params,
        comments=comments,
        custom_services=custom_services,
    )


@dataclass
class DIResolution:
    imports:            list   # [(symbol, from_module)]
    constructor_params: list   # ['private http: HttpClient', ...]
    comments:           list   # inline TODO comments for omitted tokens
    custom_services:    list   # ['UserService', 'AuthService', ...]