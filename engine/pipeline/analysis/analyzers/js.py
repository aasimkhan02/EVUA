from pathlib import Path
from typing import List, Dict, Optional
from .base import Analyzer
import esprima
import uuid


class RawController:
    def __init__(
        self,
        name: str,
        file: str,
        di: List[str],
        scope_reads: List[str],
        scope_writes: List[str],
        watch_depths: List[str],
        uses_compile: bool = False,
        has_nested_scopes: bool = False,
    ):
        self.id = str(uuid.uuid4())
        self.name = name
        self.file = file
        self.di = di
        self.scope_reads = scope_reads
        self.scope_writes = scope_writes
        self.watch_depths = watch_depths
        self.uses_compile = uses_compile
        self.has_nested_scopes = has_nested_scopes
        self.classes = []
        self.functions = []
        self.globals = []


class RawDirective:
    def __init__(self, name: str, file: str, has_compile: bool, has_link: bool, transclude: bool):
        self.id = str(uuid.uuid4())
        self.name = name
        self.file = file
        self.has_compile = has_compile
        self.has_link = has_link
        self.transclude = transclude
        self.classes = []
        self.functions = []
        self.globals = []


class RawHttpCall:
    def __init__(
        self,
        file: str,
        method: str,
        url,
        uses_q: bool,
        owner_controller: Optional[str] = None,
    ):
        self.id = str(uuid.uuid4())
        self.file = file
        self.method = method
        self.url = url
        self.uses_q = uses_q
        self.owner_controller = owner_controller
        self.classes = []
        self.functions = []
        self.globals = []


class RawRoute:
    """
    Represents a single AngularJS route extracted from $routeProvider or $stateProvider.

    Attributes
    ----------
    path          : URL path string  e.g. '/users/:id'
    controller    : Controller name  e.g. 'UserController'  (may be None)
    template_url  : templateUrl string (may be None)
    template      : inline template string (may be None)
    resolve       : dict of resolve keys → expression strings (may be empty)
    state_name    : ui-router state name  e.g. 'app.users'  (None for ngRoute)
    params        : path params extracted from path  e.g. ['id']
    is_otherwise  : True if this is the default/otherwise/catch-all route
    is_abstract   : True for ui-router abstract states
    router_type   : 'ngRoute' | 'uiRouter'
    file          : source file path
    """

    def __init__(
        self,
        path: str,
        controller: Optional[str],
        template_url: Optional[str],
        template: Optional[str],
        resolve: dict,
        state_name: Optional[str],
        is_otherwise: bool,
        is_abstract: bool,
        router_type: str,
        file: str,
        redirect_to: Optional[str] = None,
        on_enter: Optional[str] = None,
        on_exit: Optional[str] = None,
    ):
        self.id           = str(uuid.uuid4())
        self.path         = path
        self.controller   = controller
        self.template_url = template_url
        self.template     = template
        self.resolve      = resolve      # {key: expr_str}
        self.state_name   = state_name
        self.is_otherwise = is_otherwise
        self.is_abstract  = is_abstract
        self.router_type  = router_type
        self.file         = file
        # uiRouter redirect / lifecycle hooks
        self.redirect_to  = redirect_to  # redirectTo string value (if present)
        self.on_enter     = on_enter      # onEnter function name/description (if present)
        self.on_exit      = on_exit       # onExit function name/description (if present)
        # Extract :param tokens from the path
        import re
        self.params = re.findall(r':(\w+)', path or '')


def iter_children(node):
    for key, value in vars(node).items():
        if isinstance(value, list):
            for v in value:
                if hasattr(v, "type"):
                    yield v
        elif hasattr(value, "type"):
            yield value


def _extract_fn_from_arg(arg_node):
    """
    Normalises both AngularJS DI syntaxes and returns the FunctionExpression:
      Plain:  .controller('Name', function($scope) { ... })
      Array:  .controller('Name', ['$scope', '$http', function($scope, $http) { ... }])
    Returns None if neither pattern matches.
    """
    if arg_node is None:
        return None
    t = getattr(arg_node, "type", None)
    if t in ("FunctionExpression", "ArrowFunctionExpression"):
        return arg_node
    if t == "ArrayExpression":
        elements = getattr(arg_node, "elements", []) or []
        if elements:
            last = elements[-1]
            if getattr(last, "type", None) in ("FunctionExpression", "ArrowFunctionExpression"):
                return last
    return None


def _extract_di_names(arg_node) -> List[str]:
    """
    Extract DI token names from either plain-function or DI-array syntax.
    DI array is preferred because the string literals survive minification.
    """
    if arg_node is None:
        return []
    t = getattr(arg_node, "type", None)
    if t == "ArrayExpression":
        return [
            el.value
            for el in (getattr(arg_node, "elements", []) or [])
            if getattr(el, "type", None) == "Literal"
        ]
    if t in ("FunctionExpression", "ArrowFunctionExpression"):
        return [
            p.name
            for p in (getattr(arg_node, "params", []) or [])
            if getattr(p, "type", None) == "Identifier"
        ]
    return []


def _extract_string(node) -> Optional[str]:
    """Return the string value of a Literal node, or None."""
    if node is None:
        return None
    if getattr(node, "type", None) == "Literal":
        v = getattr(node, "value", None)
        return str(v) if v is not None else None
    return None


def _extract_object_prop(obj_node, key: str):
    """Return the value node for a named property in an ObjectExpression, or None."""
    if obj_node is None or getattr(obj_node, "type", None) != "ObjectExpression":
        return None
    for prop in getattr(obj_node, "properties", []) or []:
        prop_key = getattr(prop.key, "name", None) or getattr(prop.key, "value", None)
        if prop_key == key:
            return prop.value
    return None


def _extract_resolve_keys(resolve_node) -> dict:
    """
    Extract resolve block keys as {key: '<expression>'} for annotation purposes.
    We don't try to migrate the resolve logic — just capture the key names.
    """
    result = {}
    if resolve_node is None or getattr(resolve_node, "type", None) != "ObjectExpression":
        return result
    for prop in getattr(resolve_node, "properties", []) or []:
        key = getattr(prop.key, "name", None) or getattr(prop.key, "value", None)
        if key:
            result[key] = "<expression>"
    return result


# ---------------------------------------------------------------------------
# Route extraction helpers
# ---------------------------------------------------------------------------

def _parse_ngroute_config(fn_node, file_path: str) -> List[RawRoute]:
    """
    Parse a .config() function body for $routeProvider chains.

    Handles:
      $routeProvider
        .when('/path', { controller: 'Ctrl', templateUrl: '...' })
        .when('/other/:id', { ... })
        .otherwise({ redirectTo: '/path' })
    """
    routes: List[RawRoute] = []

    def scan(node):
        if node is None or not hasattr(node, "type"):
            return

        if node.type == "CallExpression":
            callee = getattr(node, "callee", None)
            args   = getattr(node, "arguments", []) or []

            if getattr(callee, "type", None) == "MemberExpression":
                method = getattr(callee.property, "name", None)

                # .when('/path', { ... })
                if method == "when" and len(args) >= 2:
                    path = _extract_string(args[0])
                    cfg  = args[1] if getattr(args[1], "type", None) == "ObjectExpression" else None

                    controller   = _extract_string(_extract_object_prop(cfg, "controller"))
                    template_url = _extract_string(_extract_object_prop(cfg, "templateUrl"))
                    template     = _extract_string(_extract_object_prop(cfg, "template"))
                    resolve_node = _extract_object_prop(cfg, "resolve")
                    resolve      = _extract_resolve_keys(resolve_node)

                    routes.append(RawRoute(
                        path=path or "/unknown",
                        controller=controller,
                        template_url=template_url,
                        template=template,
                        resolve=resolve,
                        state_name=None,
                        is_otherwise=False,
                        is_abstract=False,
                        router_type="ngRoute",
                        file=file_path,
                    ))

                # .otherwise({ redirectTo: '/path' })
                elif method == "otherwise" and len(args) >= 1:
                    cfg          = args[0] if getattr(args[0], "type", None) == "ObjectExpression" else None
                    redirect_to  = _extract_string(_extract_object_prop(cfg, "redirectTo"))
                    routes.append(RawRoute(
                        path=redirect_to or "**",
                        controller=None,
                        template_url=None,
                        template=None,
                        resolve={},
                        state_name=None,
                        is_otherwise=True,
                        is_abstract=False,
                        router_type="ngRoute",
                        file=file_path,
                    ))

                # Only follow the chain — do NOT recurse into args
                # (prevents every route being discovered O(n^2) times)
                scan(callee.object)
                return  # handled this CallExpression — skip iter_children

        # Non-CallExpression nodes: recurse normally (function body, blocks)
        for child in iter_children(node):
            scan(child)

    body = getattr(fn_node, "body", None)
    if body:
        scan(body)
    return routes


def _parse_uirouter_config(fn_node, file_path: str) -> List[RawRoute]:
    """
    Parse a .config() function body for $stateProvider chains (ui-router).

    Handles:
      $stateProvider
        .state('stateName', {
          url: '/path/:id',
          controller: 'Ctrl',
          templateUrl: '...',
          abstract: true,
          resolve: { ... }
        })
    """
    routes: List[RawRoute] = []

    def scan(node):
        if node is None or not hasattr(node, "type"):
            return

        if node.type == "CallExpression":
            callee = getattr(node, "callee", None)
            args   = getattr(node, "arguments", []) or []

            if getattr(callee, "type", None) == "MemberExpression":
                method = getattr(callee.property, "name", None)

                # .state('name', { ... })
                if method == "state" and len(args) >= 2:
                    state_name = _extract_string(args[0])
                    cfg        = args[1] if getattr(args[1], "type", None) == "ObjectExpression" else None

                    url          = _extract_string(_extract_object_prop(cfg, "url"))
                    controller   = _extract_string(_extract_object_prop(cfg, "controller"))
                    template_url = _extract_string(_extract_object_prop(cfg, "templateUrl"))
                    template     = _extract_string(_extract_object_prop(cfg, "template"))
                    resolve_node = _extract_object_prop(cfg, "resolve")
                    resolve      = _extract_resolve_keys(resolve_node)

                    # abstract: true
                    abstract_node = _extract_object_prop(cfg, "abstract")
                    is_abstract   = (
                        getattr(abstract_node, "type", None) == "Literal"
                        and getattr(abstract_node, "value", None) is True
                    )

                    # redirectTo (string or state name)
                    redirect_node = _extract_object_prop(cfg, "redirectTo")
                    redirect_to   = _extract_string(redirect_node)

                    # onEnter / onExit — capture presence (function ref or inline fn)
                    on_enter_node = _extract_object_prop(cfg, "onEnter")
                    on_exit_node  = _extract_object_prop(cfg, "onExit")
                    on_enter = (
                        getattr(on_enter_node, "name", None)
                        or ("<inline>" if on_enter_node is not None else None)
                    )
                    on_exit = (
                        getattr(on_exit_node, "name", None)
                        or ("<inline>" if on_exit_node is not None else None)
                    )

                    routes.append(RawRoute(
                        path=url or f"/{state_name or 'unknown'}",
                        controller=controller,
                        template_url=template_url,
                        template=template,
                        resolve=resolve,
                        state_name=state_name,
                        is_otherwise=False,
                        is_abstract=is_abstract,
                        router_type="uiRouter",
                        file=file_path,
                        redirect_to=redirect_to,
                        on_enter=on_enter,
                        on_exit=on_exit,
                    ))

                # Only follow the chain — do NOT recurse into args
                scan(callee.object)
                return  # handled this CallExpression — skip iter_children

        # Non-CallExpression nodes: recurse normally
        for child in iter_children(node):
            scan(child)

    body = getattr(fn_node, "body", None)
    if body:
        scan(body)
    return routes


def _handle_config_block(args, file_path: str) -> List[RawRoute]:
    """
    Given the arguments of a .config([...]) call, find the function body
    and determine which router is being configured ($routeProvider vs $stateProvider).
    """
    fn_node = _extract_fn_from_arg(args[0] if args else None)
    if fn_node is None:
        return []

    di = _extract_di_names(args[0] if args else None)
    di_lower = [d.lower() for d in di]

    if "$routeprovider" in di_lower:
        return _parse_ngroute_config(fn_node, file_path)
    elif "$stateprovider" in di_lower:
        return _parse_uirouter_config(fn_node, file_path)
    else:
        # Unknown config block — try both parsers and take whichever produces routes
        ngroute = _parse_ngroute_config(fn_node, file_path)
        if ngroute:
            return ngroute
        return _parse_uirouter_config(fn_node, file_path)


class JSAnalyzer(Analyzer):
    def analyze(self, paths: List[Path]):
        raw_modules:    List[RawController] = []
        raw_directives: List[RawDirective]  = []
        raw_http_calls: List[RawHttpCall]   = []
        raw_routes:     List[RawRoute]      = []

        # ── top-level AST traversal ────────────────────────────────────────
        def recurse(node, file_path: str, current_owner: Optional[str] = None):
            """
            current_owner: name of controller/service being parsed right now.
            Passed down into the body so $http/$q calls inside a controller
            are attributed to it, not just the file.
            """
            if node is None or not hasattr(node, "type"):
                return

            if node.type == "CallExpression":
                callee = getattr(node, "callee", None)
                args   = getattr(node, "arguments", []) or []

                if getattr(callee, "type", None) == "MemberExpression":
                    prop     = getattr(callee.property, "name", None)
                    obj_type = getattr(callee.object, "type", None)
                    obj_name = getattr(callee.object, "name", None) if obj_type == "Identifier" else None

                    # ── controller / service / factory registration ─────────
                    if prop in ("controller", "service", "factory") and len(args) >= 2:
                        name_node = args[0]
                        fn_node   = _extract_fn_from_arg(args[1])
                        if getattr(name_node, "type", None) == "Literal" and fn_node is not None:
                            ctrl_name = name_node.value
                            _handle_controller(ctrl_name, args[1], fn_node, file_path)
                            for child in iter_children(node):
                                if child is not args[1] and child is not fn_node:
                                    recurse(child, file_path, current_owner)
                            return

                    # ── directive registration ──────────────────────────────
                    elif prop == "directive" and len(args) >= 2:
                        name_node = args[0]
                        fn_node   = _extract_fn_from_arg(args[1])
                        if getattr(name_node, "type", None) == "Literal" and fn_node is not None:
                            _handle_directive(name_node.value, fn_node, file_path)

                    # ── .config([...]) — route configuration ───────────────
                    elif prop == "config" and len(args) >= 1:
                        found = _handle_config_block(args, file_path)
                        raw_routes.extend(found)
                        if found:
                            # Don't recurse further into config body — already scanned
                            for child in iter_children(node):
                                if child is not args[0]:
                                    recurse(child, file_path, current_owner)
                            return

                    # ── $http.get / post / put / delete (top-level) ─────────
                    if obj_name == "$http" and prop in ("get", "post", "put", "delete"):
                        url = None
                        if args and getattr(args[0], "type", None) == "Literal":
                            url = args[0].value
                        raw_http_calls.append(
                            RawHttpCall(file_path, prop, url,
                                        uses_q=False, owner_controller=current_owner)
                        )

                    # ── $q.defer / $q.all (top-level) ──────────────────────
                    if obj_name == "$q" and prop in ("all", "defer"):
                        raw_http_calls.append(
                            RawHttpCall(file_path, f"q_{prop}", None,
                                        uses_q=True, owner_controller=current_owner)
                        )

                # ── $http({ config }) ───────────────────────────────────────
                if (
                    getattr(callee, "type", None) == "Identifier"
                    and getattr(callee, "name", None) == "$http"
                ):
                    raw_http_calls.append(
                        RawHttpCall(file_path, "config", None,
                                    uses_q=False, owner_controller=current_owner)
                    )

            for child in iter_children(node):
                recurse(child, file_path, current_owner)

        # ── controller / service / factory body scanner ────────────────────
        def _handle_controller(name: str, raw_arg, fn_node, file_path: str):
            di             = _extract_di_names(raw_arg)
            scope_reads:  List[str] = []
            scope_writes: List[str] = []
            watch_depths: List[str] = []
            uses_compile      = False
            has_nested_scopes = False

            def scan_fn(node):
                nonlocal uses_compile, has_nested_scopes
                if node is None or not hasattr(node, "type"):
                    return

                # $scope.x = ...  → scope write
                if getattr(node, "type", None) == "AssignmentExpression":
                    left = getattr(node, "left", None)
                    if getattr(left, "type", None) == "MemberExpression":
                        obj  = getattr(left, "object", None)
                        prop = getattr(left, "property", None)
                        if (
                            getattr(obj, "type", None) == "Identifier"
                            and getattr(obj, "name", None) == "$scope"
                        ):
                            pname = getattr(prop, "name", None) or getattr(prop, "value", None)
                            if pname:
                                scope_writes.append(pname)

                # var x = $scope.$new()  → nested scope
                if getattr(node, "type", None) == "VariableDeclarator":
                    init = getattr(node, "init", None)
                    if init:
                        if getattr(init, "type", None) == "CallExpression":
                            callee = getattr(init, "callee", None)
                            if (
                                getattr(callee, "type", None) == "MemberExpression"
                                and getattr(callee.object, "type", None) == "Identifier"
                                and getattr(callee.object, "name", None) == "$scope"
                                and getattr(callee.property, "name", None) == "$new"
                            ):
                                has_nested_scopes = True
                        scan_fn(init)

                if getattr(node, "type", None) == "CallExpression":
                    callee   = getattr(node, "callee", None)
                    callargs = getattr(node, "arguments", []) or []

                    if getattr(callee, "type", None) == "MemberExpression":
                        obj_type = getattr(callee.object, "type", None)
                        obj_name = getattr(callee.object, "name", None) if obj_type == "Identifier" else None
                        pname    = getattr(callee.property, "name", None)

                        if obj_name == "$scope":
                            # $scope.$watch(...)
                            if pname == "$watch":
                                is_deep = False
                                if len(callargs) >= 3:
                                    third = callargs[2]
                                    if (
                                        getattr(third, "type", None) == "Literal"
                                        and getattr(third, "value", None) is True
                                    ):
                                        is_deep = True
                                watch_depths.append("deep" if is_deep else "shallow")
                            if pname == "$new":
                                has_nested_scopes = True

                        # $http calls INSIDE controller body → attribute to this controller
                        if obj_name == "$http" and pname in ("get", "post", "put", "delete"):
                            url = None
                            if callargs and getattr(callargs[0], "type", None) == "Literal":
                                url = callargs[0].value
                            raw_http_calls.append(
                                RawHttpCall(file_path, pname, url,
                                            uses_q=False, owner_controller=name)
                            )

                        # $q.defer / $q.all INSIDE controller body
                        if obj_name == "$q" and pname in ("defer", "all"):
                            raw_http_calls.append(
                                RawHttpCall(file_path, f"q_{pname}", None,
                                            uses_q=True, owner_controller=name)
                            )

                    # $compile(...)
                    if (
                        getattr(callee, "type", None) == "Identifier"
                        and getattr(callee, "name", None) == "$compile"
                    ):
                        uses_compile = True

                # $scope.x  → scope read
                if getattr(node, "type", None) == "MemberExpression":
                    obj  = getattr(node, "object", None)
                    prop = getattr(node, "property", None)
                    if (
                        getattr(obj, "type", None) == "Identifier"
                        and getattr(obj, "name", None) == "$scope"
                    ):
                        pname = getattr(prop, "name", None) or getattr(prop, "value", None)
                        if pname:
                            scope_reads.append(pname)

                for child in iter_children(node):
                    scan_fn(child)

            body = getattr(fn_node, "body", None)
            if body:
                scan_fn(body)

            raw_modules.append(RawController(
                name=name,
                file=file_path,
                di=di,
                scope_reads=scope_reads,
                scope_writes=scope_writes,
                watch_depths=watch_depths,
                uses_compile=uses_compile,
                has_nested_scopes=has_nested_scopes,
            ))

        # ── directive body scanner ─────────────────────────────────────────
        def _handle_directive(name: str, fn_node, file_path: str):
            has_compile = False
            has_link    = False
            transclude  = False

            def scan_for_return(node):
                nonlocal has_compile, has_link, transclude
                if node is None or not hasattr(node, "type"):
                    return
                if getattr(node, "type", None) == "ReturnStatement":
                    arg = getattr(node, "argument", None)
                    if arg and getattr(arg, "type", None) == "ObjectExpression":
                        for prop in getattr(arg, "properties", []) or []:
                            key = getattr(prop.key, "name", None) or getattr(prop.key, "value", None)
                            val = getattr(prop, "value", None)
                            if key == "compile":   has_compile = True
                            if key == "link":      has_link    = True
                            if key == "transclude":
                                if getattr(val, "type", None) == "Literal" and getattr(val, "value", None) is True:
                                    transclude = True
                if getattr(node, "type", None) == "Property":
                    key = getattr(node.key, "name", None) or getattr(node.key, "value", None)
                    if key == "compile":   has_compile = True
                    if key == "link":      has_link    = True
                    if key == "transclude":
                        val = getattr(node, "value", None)
                        if getattr(val, "type", None) == "Literal" and getattr(val, "value", None) is True:
                            transclude = True
                for child in iter_children(node):
                    scan_for_return(child)

            scan_for_return(fn_node)
            raw_directives.append(RawDirective(
                name=name, file=file_path,
                has_compile=has_compile, has_link=has_link, transclude=transclude,
            ))

        # ── parse each file ────────────────────────────────────────────────
        for path in paths:
            text = path.read_text(encoding="utf-8", errors="ignore")
            try:
                ast = esprima.parseScript(text, tolerant=True)
            except Exception:
                continue
            recurse(ast, str(path), current_owner=None)

        # ── deduplicate http calls ─────────────────────────────────────────
        deduped: List[RawHttpCall] = []
        seen: Dict[tuple, int] = {}

        for call in raw_http_calls:
            sig = (call.file, call.method, call.url)
            if sig in seen:
                existing = deduped[seen[sig]]
                if call.owner_controller and not existing.owner_controller:
                    deduped[seen[sig]] = call
            else:
                seen[sig] = len(deduped)
                deduped.append(call)

        return raw_modules, [], [], raw_directives, deduped, raw_routes