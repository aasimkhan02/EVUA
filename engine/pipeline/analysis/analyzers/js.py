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
        scope_methods: List[dict],
        init_calls: List[str],
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
        self.scope_methods = scope_methods
        self.init_calls = init_calls
        self.watch_depths = watch_depths
        self.uses_compile = uses_compile
        self.has_nested_scopes = has_nested_scopes
        self.is_component = False   # True when registered via .component() not .controller()
        self.classes = []
        self.functions = []
        self.globals = []


class RawDirective:
    def __init__(self, name: str, file: str, has_compile: bool, has_link: bool, transclude: bool,
                 restrict: str = 'EA', scope_bindings: dict = None,
                 template: str = None, template_url: str = None):
        self.id = str(uuid.uuid4())
        self.name = name
        self.file = file
        self.has_compile = has_compile
        self.has_link = has_link
        self.transclude = transclude
        self.restrict = restrict               # 'E', 'A', 'EA', 'C', etc.
        self.scope_bindings = scope_bindings or {}  # {bindingName: '@'/'='/'&'}
        self.template = template               # inline template string
        self.template_url = template_url       # templateUrl string
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
        owner_method: Optional[str] = None,
        has_catch: bool = False,
        # NEW: raw source text of chained .then() and .catch() callback bodies
        then_body_src: Optional[str] = None,
        catch_body_src: Optional[str] = None,
        request_body_src: Optional[str] = None,   # second arg to $http.post/put/patch
    ):
        self.id = str(uuid.uuid4())
        self.file = file
        self.method = method
        self.url = url
        self.uses_q = uses_q
        self.owner_controller = owner_controller
        self.owner_method = owner_method
        self.has_catch = has_catch
        self.then_body_src = then_body_src
        self.catch_body_src = catch_body_src
        self.request_body_src = request_body_src
        self.classes = []
        self.functions = []
        self.globals = []


class RawRoute:
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
        self.resolve      = resolve
        self.state_name   = state_name
        self.is_otherwise = is_otherwise
        self.is_abstract  = is_abstract
        self.router_type  = router_type
        self.file         = file
        self.redirect_to  = redirect_to
        self.on_enter     = on_enter
        self.on_exit      = on_exit
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
    if node is None:
        return None
    if getattr(node, "type", None) == "Literal":
        v = getattr(node, "value", None)
        return str(v) if v is not None else None
    return None


def _extract_object_prop(obj_node, key: str):
    if obj_node is None or getattr(obj_node, "type", None) != "ObjectExpression":
        return None
    for prop in getattr(obj_node, "properties", []) or []:
        prop_key = getattr(prop.key, "name", None) or getattr(prop.key, "value", None)
        if prop_key == key:
            return prop.value
    return None


def _extract_resolve_keys(resolve_node) -> dict:
    result = {}
    if resolve_node is None or getattr(resolve_node, "type", None) != "ObjectExpression":
        return result
    for prop in getattr(resolve_node, "properties", []) or []:
        key = getattr(prop.key, "name", None) or getattr(prop.key, "value", None)
        if key:
            result[key] = "<expression>"
    return result


# ---------------------------------------------------------------------------
# NEW: helpers to extract then/catch callback source text
# ---------------------------------------------------------------------------

def _fn_body_src(fn_node, source: str) -> Optional[str]:
    """
    Return the *inner* source text of a function body (the statements between
    the outer braces), or None if we can't determine it.
    """
    if fn_node is None:
        return None
    body = getattr(fn_node, "body", None)
    if body is None:
        return None
    start = getattr(body, "range", None)
    if start is None:
        # esprima may not include range unless we pass range=True at parse time
        return None
    lo, hi = body.range
    # Strip outer braces and dedent one level
    inner = source[lo + 1: hi - 1].strip()
    return inner or None


def _extract_chain_callbacks(call_node, source: str):
    """
    Walk a .then(...).catch(...) chain rooted at *call_node* and return
    (then_body_src, catch_body_src).  Both may be None.

    The AST looks like:

        CallExpression          ← .catch(fn)
          callee: MemberExpression
            object: CallExpression   ← .then(fn)
              callee: MemberExpression
                object: CallExpression  ← $http.get(url)
            property: 'then'
          property: 'catch'
    """
    then_src  = None
    catch_src = None

    node = call_node
    while True:
        if getattr(node, "type", None) != "CallExpression":
            break
        callee = getattr(node, "callee", None)
        if getattr(callee, "type", None) != "MemberExpression":
            break
        prop = getattr(callee.property, "name", None)
        args = getattr(node, "arguments", []) or []
        fn   = args[0] if args else None

        if prop == "then" and then_src is None:
            then_src = _fn_body_src(_extract_fn_from_arg(fn), source) if fn else None
        elif prop == "catch" and catch_src is None:
            catch_src = _fn_body_src(_extract_fn_from_arg(fn), source) if fn else None

        # Move inward along the chain
        node = callee.object

    return then_src, catch_src


# ---------------------------------------------------------------------------
# Route extraction helpers (unchanged)
# ---------------------------------------------------------------------------

def _parse_ngroute_config(fn_node, file_path: str) -> List[RawRoute]:
    routes: List[RawRoute] = []

    def scan(node):
        if node is None or not hasattr(node, "type"):
            return
        if node.type == "CallExpression":
            callee = getattr(node, "callee", None)
            args   = getattr(node, "arguments", []) or []
            if getattr(callee, "type", None) == "MemberExpression":
                method = getattr(callee.property, "name", None)
                if method == "when" and len(args) >= 2:
                    path = _extract_string(args[0])
                    cfg  = args[1] if getattr(args[1], "type", None) == "ObjectExpression" else None
                    controller   = _extract_string(_extract_object_prop(cfg, "controller"))
                    template_url = _extract_string(_extract_object_prop(cfg, "templateUrl"))
                    template     = _extract_string(_extract_object_prop(cfg, "template"))
                    resolve_node = _extract_object_prop(cfg, "resolve")
                    resolve      = _extract_resolve_keys(resolve_node)
                    routes.append(RawRoute(
                        path=path or "/unknown", controller=controller,
                        template_url=template_url, template=template, resolve=resolve,
                        state_name=None, is_otherwise=False, is_abstract=False,
                        router_type="ngRoute", file=file_path,
                    ))
                elif method == "otherwise" and len(args) >= 1:
                    cfg         = args[0] if getattr(args[0], "type", None) == "ObjectExpression" else None
                    redirect_to = _extract_string(_extract_object_prop(cfg, "redirectTo"))
                    routes.append(RawRoute(
                        path=redirect_to or "**", controller=None,
                        template_url=None, template=None, resolve={},
                        state_name=None, is_otherwise=True, is_abstract=False,
                        router_type="ngRoute", file=file_path,
                    ))
                scan(callee.object)
                return
        for child in iter_children(node):
            scan(child)

    body = getattr(fn_node, "body", None)
    if body:
        scan(body)
    return routes


def _parse_uirouter_config(fn_node, file_path: str) -> List[RawRoute]:
    routes: List[RawRoute] = []

    def scan(node):
        if node is None or not hasattr(node, "type"):
            return
        if node.type == "CallExpression":
            callee = getattr(node, "callee", None)
            args   = getattr(node, "arguments", []) or []
            if getattr(callee, "type", None) == "MemberExpression":
                method = getattr(callee.property, "name", None)
                if method == "state" and len(args) >= 2:
                    state_name   = _extract_string(args[0])
                    cfg          = args[1] if getattr(args[1], "type", None) == "ObjectExpression" else None
                    url          = _extract_string(_extract_object_prop(cfg, "url"))
                    controller   = _extract_string(_extract_object_prop(cfg, "controller"))
                    template_url = _extract_string(_extract_object_prop(cfg, "templateUrl"))
                    template     = _extract_string(_extract_object_prop(cfg, "template"))
                    resolve_node = _extract_object_prop(cfg, "resolve")
                    resolve      = _extract_resolve_keys(resolve_node)
                    abstract_node = _extract_object_prop(cfg, "abstract")
                    is_abstract   = (
                        getattr(abstract_node, "type", None) == "Literal"
                        and getattr(abstract_node, "value", None) is True
                    )
                    redirect_node = _extract_object_prop(cfg, "redirectTo")
                    redirect_to   = _extract_string(redirect_node)
                    on_enter_node = _extract_object_prop(cfg, "onEnter")
                    on_exit_node  = _extract_object_prop(cfg, "onExit")
                    on_enter = getattr(on_enter_node, "name", None) or ("<inline>" if on_enter_node else None)
                    on_exit  = getattr(on_exit_node,  "name", None) or ("<inline>" if on_exit_node  else None)
                    routes.append(RawRoute(
                        path=url or f"/{state_name or 'unknown'}",
                        controller=controller, template_url=template_url,
                        template=template, resolve=resolve, state_name=state_name,
                        is_otherwise=False, is_abstract=is_abstract,
                        router_type="uiRouter", file=file_path,
                        redirect_to=redirect_to, on_enter=on_enter, on_exit=on_exit,
                    ))
                scan(callee.object)
                return
        for child in iter_children(node):
            scan(child)

    body = getattr(fn_node, "body", None)
    if body:
        scan(body)
    return routes


def _handle_config_block(args, file_path: str) -> List[RawRoute]:
    fn_node = _extract_fn_from_arg(args[0] if args else None)
    if fn_node is None:
        return []
    di       = _extract_di_names(args[0] if args else None)
    di_lower = [d.lower() for d in di]
    if "$routeprovider" in di_lower:
        return _parse_ngroute_config(fn_node, file_path)
    elif "$stateprovider" in di_lower:
        return _parse_uirouter_config(fn_node, file_path)
    else:
        ngroute = _parse_ngroute_config(fn_node, file_path)
        if ngroute:
            return ngroute
        return _parse_uirouter_config(fn_node, file_path)


def _collect_module_aliases(ast, aliases: dict):
    """
    First-pass walk: find patterns like:
      var app = angular.module('myApp', []);
      let app = angular.module('myApp', []);
      app = angular.module('myApp', []);
    and populate aliases = {'app': 'myApp'}.
    """
    def _walk(node):
        if node is None or not hasattr(node, "type"):
            return

        # var/let/const x = angular.module(...)
        if getattr(node, "type", None) == "VariableDeclarator":
            id_node   = getattr(node, "id", None)
            init_node = getattr(node, "init", None)
            var_name  = getattr(id_node, "name", None) if id_node else None
            if var_name and _is_angular_module_call(init_node):
                aliases[var_name] = _get_module_name(init_node)

        # x = angular.module(...)  (bare assignment)
        if getattr(node, "type", None) == "AssignmentExpression":
            left     = getattr(node, "left", None)
            right    = getattr(node, "right", None)
            var_name = getattr(left, "name", None) if getattr(left, "type", None) == "Identifier" else None
            if var_name and _is_angular_module_call(right):
                aliases[var_name] = _get_module_name(right)

        for key in vars(node):
            val = getattr(node, key, None)
            if val is None:
                continue
            if hasattr(val, "type"):
                _walk(val)
            elif isinstance(val, list):
                for item in val:
                    if hasattr(item, "type"):
                        _walk(item)

    _walk(ast)


def _is_angular_module_call(node) -> bool:
    """Return True if node is angular.module(...) call."""
    if node is None or getattr(node, "type", None) != "CallExpression":
        return False
    callee = getattr(node, "callee", None)
    if getattr(callee, "type", None) != "MemberExpression":
        return False
    obj  = getattr(callee, "object", None)
    prop = getattr(callee, "property", None)
    return (
        getattr(obj, "name", None) == "angular"
        and getattr(prop, "name", None) == "module"
    )


def _get_module_name(node) -> str:
    """Extract the first string arg from angular.module('name', [...])."""
    args = getattr(node, "arguments", []) or []
    if args and getattr(args[0], "type", None) == "Literal":
        return str(args[0].value)
    return "<unknown>"


class JSAnalyzer(Analyzer):
    def analyze(self, paths: List[Path]):
        raw_modules:    List[RawController] = []
        raw_directives: List[RawDirective]  = []
        raw_http_calls: List[RawHttpCall]   = []
        raw_routes:     List[RawRoute]      = []
        raw_filters:    List[dict]          = [] 

        def recurse(node, file_path: str, source: str, current_owner: Optional[str] = None,
                    module_aliases: Optional[Dict[str, str]] = None):
            if node is None or not hasattr(node, "type"):
                return

            if node.type == "CallExpression":
                callee = getattr(node, "callee", None)
                args   = getattr(node, "arguments", []) or []

                if getattr(callee, "type", None) == "MemberExpression":
                    prop     = getattr(callee.property, "name", None)
                    obj_type = getattr(callee.object, "type", None)
                    obj_name = getattr(callee.object, "name", None) if obj_type == "Identifier" else None

                    # Detect alias-based calls: app.controller(...) where app is a known module alias
                    _is_module_alias_call = (
                        obj_name is not None
                        and module_aliases is not None
                        and obj_name in module_aliases
                    )

                    # Detect chained: angular.module('x').component(...)
                    _is_chained_module_component = False

                    if obj_type == "CallExpression":
                        inner_callee = getattr(callee.object, "callee", None)
                        if getattr(inner_callee, "type", None) == "MemberExpression":
                            inner_obj  = getattr(inner_callee.object, "name", None)
                            inner_prop = getattr(inner_callee.property, "name", None)

                            if inner_obj == "angular" and inner_prop == "module":
                                _is_chained_module_component = True

                    if prop in ("controller", "service", "factory") and len(args) >= 2:
                        name_node = args[0]
                        fn_node   = _extract_fn_from_arg(args[1])
                        if getattr(name_node, "type", None) == "Literal" and fn_node is not None:
                            ctrl_name = name_node.value
                            _handle_controller(ctrl_name, args[1], fn_node, file_path, source)
                            for child in iter_children(node):
                                if child is not args[1] and child is not fn_node:
                                    recurse(child, file_path, source, current_owner, module_aliases)
                            return

                    # AngularJS 1.5+ .component('name', { controller: fn, template: '...' })
                    # Matches alias-based (app.component) AND chained (angular.module('x').component(...))
                    elif prop == "component" and len(args) >= 2 and (
                            _is_module_alias_call or _is_chained_module_component
                        ):
                        name_node = args[0]
                        cfg_node  = args[1] if getattr(args[1], "type", None) == "ObjectExpression" else None

                        if getattr(name_node, "type", None) == "Literal" and cfg_node is not None:
                            comp_name = name_node.value

                            # Extract controller from component config
                            ctrl_prop = _extract_object_prop(cfg_node, "controller")
                            fn_node = None

                            # inline controller
                            if ctrl_prop and getattr(ctrl_prop, "type", None) in (
                                "FunctionExpression",
                                "ArrowFunctionExpression"
                            ):
                                fn_node = ctrl_prop

                            # DI array syntax
                            elif ctrl_prop and getattr(ctrl_prop, "type", None) == "ArrayExpression":
                                elements = getattr(ctrl_prop, "elements", []) or []
                                if elements:
                                    last = elements[-1]
                                    if getattr(last, "type", None) in (
                                        "FunctionExpression",
                                        "ArrowFunctionExpression"
                                    ):
                                        fn_node = last
                            # If no inline function, synthesise a minimal fn_node placeholder
                            # We still create a controller entry so the component is detected
                            if fn_node is None and ctrl_prop is not None:
                                # Named controller reference — record with empty body
                                ctrl_name_ref = getattr(ctrl_prop, "name", None)
                                if ctrl_name_ref:
                                    print(f"[js.py] .component('{comp_name}') references named ctrl {ctrl_name_ref}")
                            if fn_node is not None:
                                # treat AngularJS .component() like a controller for migration
                                _handle_controller(comp_name, ctrl_prop, fn_node, file_path, source, is_component=True)

                                print(f"[js.py] .component('{comp_name}') controller detected")
                            elif cfg_node is not None:
                                # No controller function found — register component with empty body
                                ctrl = RawController(
                                    name=comp_name, file=file_path, di=[],
                                    scope_reads=[], scope_writes=[], scope_methods=[],
                                    init_calls=[], watch_depths=[],
                                )
                                ctrl.is_component = True
                                ctrl.kind = "component"
                                raw_modules.append(ctrl)
                                print(f"[js.py] .component('{comp_name}') registered (no inline controller)")
                            for child in iter_children(node):
                                recurse(child, file_path, source, current_owner, module_aliases)
                            return

                    elif prop == "directive" and len(args) >= 2:
                        name_node = args[0]
                        fn_node   = _extract_fn_from_arg(args[1])
                        if getattr(name_node, "type", None) == "Literal" and fn_node is not None:
                            _handle_directive(name_node.value, fn_node, file_path)

                    elif prop == "filter" and len(args) >= 2:
                        name_node = args[0]
                        fn_node   = _extract_fn_from_arg(args[1])

                        if getattr(name_node, "type", None) == "Literal":
                            fname = name_node.value
                            body_src = _fn_body_src(fn_node, source) if fn_node else None

                            raw_filters.append({
                                "name": fname,
                                "fn_body": body_src
                            })

                    elif prop == "config" and len(args) >= 1:
                        found = _handle_config_block(args, file_path)
                        raw_routes.extend(found)
                        if found:
                            for child in iter_children(node):
                                if child is not args[0]:
                                    recurse(child, file_path, source, current_owner, module_aliases)
                            return

                    if obj_name == "$http" and prop in ("get", "post", "put", "delete"):
                        url = None
                        if args and getattr(args[0], "type", None) == "Literal":
                            url = args[0].value
                        raw_http_calls.append(
                            RawHttpCall(file_path, prop, url,
                                        uses_q=False, owner_controller=current_owner)
                        )

                    if obj_name == "$q" and prop in ("all", "defer"):
                        raw_http_calls.append(
                            RawHttpCall(file_path, f"q_{prop}", None,
                                        uses_q=True, owner_controller=current_owner)
                        )

                if (
                    getattr(callee, "type", None) == "Identifier"
                    and getattr(callee, "name", None) == "$http"
                ):
                    raw_http_calls.append(
                        RawHttpCall(file_path, "config", None,
                                    uses_q=False, owner_controller=current_owner)
                    )

            for child in iter_children(node):
                recurse(child, file_path, source, current_owner, module_aliases)

        # ── controller / service / factory body scanner ────────────────────
        def _handle_controller(name: str, raw_arg, fn_node, file_path: str, source: str, is_component=False):
            di              = _extract_di_names(raw_arg)
            scope_reads:   List[str]  = []
            scope_writes:  List[str]  = []
            scope_methods: List[dict] = []
            init_calls:    List[str]  = []
            watch_depths:  List[str]  = []
            uses_compile      = False
            has_nested_scopes = False
            self_aliases: set = set()   # tracks var self=this / var vm=this aliases

            def _scan_method_http(fn_body, method_name: str, ctrl_name: str, fpath: str):
                """
                Scan a $scope method body for $http calls.

                For each call node we walk UP the AST of *fn_body* to detect
                .then() / .catch() wrappers and extract their callback source.

                Because esprima doesn't attach parent pointers, we do a single
                pre-pass to build a child→parent map restricted to fn_body.
                """
                print("[js.py DEBUG] _scan_method_http called: ctrl=" + repr(ctrl_name) + " method=" + repr(method_name))

                # ── Build child→parent map inside fn_body ──────────────
                parent_of: Dict[int, object] = {}   # id(node) → parent node

                def _index(n, par=None):
                    if n is None or not hasattr(n, "type"):
                        return
                    parent_of[id(n)] = par
                    for key in vars(n):
                        val = getattr(n, key, None)
                        if val is None:
                            continue
                        if hasattr(val, "type"):
                            _index(val, n)
                        elif isinstance(val, list):
                            for item in val:
                                if hasattr(item, "type"):
                                    _index(item, n)

                _index(fn_body)

                def _find_wrapping_chain(http_call_node):
                    """
                    Walk upward from the $http.xyz() call node to find if it is
                    immediately wrapped in .then().catch() chains.
                    Returns (has_catch, then_src, catch_src).
                    """
                    then_src  = None
                    catch_src = None
                    has_catch = False

                    cur = http_call_node
                    while True:
                        par = parent_of.get(id(cur))
                        if par is None:
                            break
                        # par should be a MemberExpression (the .then/.catch property access)
                        if getattr(par, "type", None) != "MemberExpression":
                            break
                        prop_name = getattr(par.property, "name", None)
                        # The MemberExpression's parent should be the CallExpression for .then()/.catch()
                        call_node = parent_of.get(id(par))
                        if call_node is None or getattr(call_node, "type", None) != "CallExpression":
                            break
                        call_args = getattr(call_node, "arguments", []) or []
                        fn_arg    = call_args[0] if call_args else None

                        if prop_name == "then" and then_src is None:
                            inner_fn = _extract_fn_from_arg(fn_arg)
                            then_src = _fn_body_src(inner_fn, source)
                        elif prop_name == "catch" and catch_src is None:
                            has_catch = True
                            inner_fn  = _extract_fn_from_arg(fn_arg)
                            catch_src = _fn_body_src(inner_fn, source)

                        cur = call_node   # keep walking up

                    return has_catch, then_src, catch_src

                def _walk(n):
                    if n is None or not hasattr(n, "type"):
                        return
                    if getattr(n, "type", None) == "CallExpression":
                        cal   = getattr(n, "callee", None)
                        cargs = getattr(n, "arguments", []) or []
                        if getattr(cal, "type", None) == "MemberExpression":
                            cobj  = getattr(cal.object, "type", None)
                            cname = getattr(cal.object, "name", None) if cobj == "Identifier" else None
                            cprop = getattr(cal.property, "name", None)

                            if cname == "$http" and cprop in ("get", "post", "put", "delete", "patch"):
                                url = None
                                url_src = None

                                if cargs:
                                    arg0 = cargs[0]

                                    if getattr(arg0, "type", None) == "Literal":
                                        url = arg0.value
                                    else:
                                        rng = getattr(arg0, "range", None)
                                        if rng:
                                            url_src = source[rng[0]:rng[1]]

                                # Request body: second arg for post/put/patch
                                req_body_src = None
                                if cprop in ("post", "put", "patch") and len(cargs) >= 2:
                                    rb = cargs[1]
                                    rb_range = getattr(rb, "range", None)
                                    if rb_range:
                                        req_body_src = source[rb_range[0]:rb_range[1]]

                                has_catch, then_src, catch_src = _find_wrapping_chain(n)

                                call = RawHttpCall(
                                    fpath, cprop, url,
                                    uses_q=False,
                                    owner_controller=ctrl_name,
                                    owner_method=method_name,
                                    has_catch=has_catch,
                                    then_body_src=then_src,
                                    catch_body_src=catch_src,
                                    request_body_src=req_body_src,
                                )

                                # Preserve dynamic URL source if URL literal was not detected
                                call.url_src = url_src

                                raw_http_calls.append(call)
                                return  # don't recurse into the $http call itself

                            if cname == "$q" and cprop in ("defer", "all"):
                                raw_http_calls.append(
                                    RawHttpCall(fpath, f"q_{cprop}", None,
                                                uses_q=True,
                                                owner_controller=ctrl_name,
                                                owner_method=method_name)
                                )
                                return

                    for key in ["body", "expression", "callee", "object", "property",
                                "left", "right", "argument", "arguments", "params",
                                "declarations", "init", "consequent", "alternate", "block",
                                "test", "cases", "elements", "properties", "handler", "finalizer"]:
                        val = getattr(n, key, None)
                        if val is None:
                            continue
                        if hasattr(val, "type"):
                            _walk(val)
                        elif isinstance(val, list):
                            for item in val:
                                if hasattr(item, "type"):
                                    _walk(item)

                _walk(fn_body)

            def scan_fn(node, _current_method=None):
                nonlocal uses_compile, has_nested_scopes

                # ── var self = this  /  var vm = this ──────────────────────
                if getattr(node, "type", None) == "VariableDeclarator":
                    _vid   = getattr(node, "id", None)
                    _vinit = getattr(node, "init", None)

                    if (
                        getattr(_vid, "type", None) == "Identifier"
                        and getattr(_vinit, "type", None) == "ThisExpression"
                    ):
                        alias = _vid.name

                        # common AngularJS controller aliases
                        if alias in ("self", "vm", "ctrl", "that") or True:
                            self_aliases.add(alias)
                            print(f"[js.py] {name}: self alias '{alias}' = this")
                if node is None or not hasattr(node, "type"):
                    return

                if getattr(node, "type", None) == "AssignmentExpression":
                    left  = getattr(node, "left", None)
                    right = getattr(node, "right", None)
                    if getattr(left, "type", None) == "MemberExpression":
                        obj  = getattr(left, "object", None)
                        prop = getattr(left, "property", None)
                        if (
                            getattr(obj, "type", None) == "Identifier"
                            and getattr(obj, "name", None) == "$scope"
                        ):
                            pname = getattr(prop, "name", None) or getattr(prop, "value", None)
                            if pname and not pname.startswith("$"):
                                rtype = getattr(right, "type", None)
                                if rtype in ("FunctionExpression", "ArrowFunctionExpression"):
                                    params = [
                                        getattr(p, "name", "arg")
                                        for p in (getattr(right, "params", []) or [])
                                        if getattr(p, "type", None) == "Identifier"
                                    ]
                                    scope_methods.append({"name": pname, "params": params})
                                    fn_body = getattr(right, "body", None)
                                    if fn_body:
                                        _scan_method_http(fn_body, pname, name, file_path)
                                else:
                                    scope_writes.append(pname)

                # this.method = function() for service bodies
                # Also: self.method = function() when self_aliases contains 'self'
                if getattr(node, "type", None) == "AssignmentExpression":
                    _sl = getattr(node, "left", None)
                    _sr = getattr(node, "right", None)
                    if getattr(_sl, "type", None) == "MemberExpression":
                        _so = getattr(_sl, "object", None)
                        _sp = getattr(_sl, "property", None)
                        _is_this = getattr(_so, "type", None) == "ThisExpression"
                        _is_self = (getattr(_so, "type", None) == "Identifier"
                                    and getattr(_so, "name", None) in self_aliases)
                        if _is_this or _is_self:
                            _sname = getattr(_sp, "name", None) or getattr(_sp, "value", None)
                            if _sname and not _sname.startswith("_"):
                                _srtype = getattr(_sr, "type", None)
                                if _srtype in ("FunctionExpression", "ArrowFunctionExpression"):
                                    _sparams = [
                                        getattr(p, "name", "arg")
                                        for p in (getattr(_sr, "params", []) or [])
                                        if getattr(p, "type", None) == "Identifier"
                                    ]
                                    if not any(m["name"] == _sname for m in scope_methods):
                                        scope_methods.append({"name": _sname, "params": _sparams, "is_this_method": True})
                                    _sfn_body = getattr(_sr, "body", None)
                                    print("[js.py DEBUG] this.method block: " + repr(_sname) + " sfn_body=" + repr(_sfn_body is not None))
                                    if _sfn_body:
                                        # Tag HTTP calls with owner_method via _scan_method_http
                                        _scan_method_http(_sfn_body, _sname, name, file_path)
                                        # Also recurse with _current_method set so scan_fn skips (no double-add)
                                        scan_fn(_sfn_body, _current_method=_sname)
                                    # Scan non-body children without method context
                                    for _sc in iter_children(_sr):
                                        if _sc is not _sfn_body:
                                            scan_fn(_sc, _current_method)
                                    for _sc in iter_children(_sl):
                                        scan_fn(_sc, _current_method)
                                    print("[js.py DEBUG] this.method returning early for " + repr(_sname))
                                    return

                if getattr(node, "type", None) == "CallExpression":
                    callee_node = getattr(node, "callee", None)
                    if getattr(callee_node, "type", None) == "MemberExpression":
                        cobj  = getattr(callee_node, "object", None)
                        cprop = getattr(callee_node, "property", None)
                        _cname = getattr(cobj, "name", None) if getattr(cobj, "type", None) == "Identifier" else None
                        if _cname == "$scope":
                            fn_called = getattr(cprop, "name", None)
                            if fn_called and not fn_called.startswith("$"):
                                if fn_called not in init_calls:
                                    init_calls.append(fn_called)
                        # self.loadData() / vm.loadData() at controller body level → ngOnInit
                        elif _cname in self_aliases:
                            fn_called = getattr(cprop, "name", None)

                            if (
                                fn_called
                                and not fn_called.startswith("$")
                                and fn_called not in init_calls
                            ):
                                init_calls.append(fn_called)

                # Bare call: load(); loadData(); at controller body level
                if getattr(node, "type", None) == "CallExpression":
                    _bcallee = getattr(node, "callee", None)
                    if getattr(_bcallee, "type", None) == "Identifier":
                        _bname = getattr(_bcallee, "name", None)
                        if _bname and not _bname.startswith("$") and _bname not in init_calls:
                            init_calls.append(_bname)

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
                            if pname in ("$watch", "$watchCollection", "$watchGroup"):
                                is_deep = False
                                if pname == "$watchCollection":
                                    # $watchCollection is always a shallow collection watch
                                    watch_depths.append("collection")
                                elif pname == "$watchGroup":
                                    watch_depths.append("group")
                                else:
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

                        if obj_name == "$http" and pname in ("get", "post", "put", "delete"):
                            url_dbg = None
                            if callargs and getattr(callargs[0], "type", None) == "Literal":
                                url_dbg = callargs[0].value
                            print("[js.py DEBUG] $http." + pname + "(" + str(url_dbg) + ") in " + name + " _current_method=" + repr(_current_method) + (" -> SKIPPED" if _current_method else " -> ADDED"))
                            if _current_method is None:
                                raw_http_calls.append(
                                    RawHttpCall(file_path, pname, url_dbg,
                                                uses_q=False, owner_controller=name)
                                )

                        if obj_name == "$q" and pname in ("defer", "all"):
                            print("[js.py DEBUG] $q." + pname + "() in " + name + " _current_method=" + repr(_current_method))
                            if _current_method is None:
                                raw_http_calls.append(
                                    RawHttpCall(file_path, f"q_{pname}", None,
                                                uses_q=True, owner_controller=name)
                                )

                    if (
                        getattr(callee, "type", None) == "Identifier"
                        and getattr(callee, "name", None) == "$compile"
                    ):
                        uses_compile = True

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

                _nt = getattr(node, "type", None)
                if _nt == "AssignmentExpression":
                    _lft = getattr(node, "left", None)
                    _rgt = getattr(node, "right", None)
                    if getattr(_lft, "type", None) == "MemberExpression":
                        _ot = getattr(_lft.object, "type", None) if _lft else None
                        _on = getattr(_lft.object, "name", None) if _ot == "Identifier" else None
                        _pn = getattr(_lft.property, "name", None) if _lft else None
                        _rt = getattr(_rgt, "type", None)
                        if (_on == "$scope" and _pn and not _pn.startswith("$") and
                                _rt in ("FunctionExpression", "ArrowFunctionExpression")):
                            _fb = getattr(_rgt, "body", None)
                            if _fb:
                                scan_fn(_fb, _current_method=_pn)
                            for _c in iter_children(_rgt):
                                if _c is not _fb:
                                    scan_fn(_c, _current_method)
                            for _c in iter_children(_lft):
                                scan_fn(_c, _current_method)
                            return

                for child in iter_children(node):
                    scan_fn(child, _current_method)

            body = getattr(fn_node, "body", None)
            if body:
                scan_fn(body)

            _owned   = [c for c in raw_http_calls if getattr(c, "owner_method", None) and getattr(c, "owner_controller", None) == name]
            _unowned = [c for c in raw_http_calls if not getattr(c, "owner_method", None) and getattr(c, "owner_controller", None) == name]
            print("[js.py DEBUG] Controller " + repr(name) + ": " + str(len(_owned)) + " method-owned, " + str(len(_unowned)) + " top-level, scope_methods=" + str([m["name"] for m in scope_methods]) + ", init_calls_raw=" + str(init_calls))
            print("[js.py DEBUG]   owned calls: " + str([(getattr(c,"owner_method",None), c.method, c.url) for c in _owned]))
            print("[js.py DEBUG]   unowned calls: " + str([(c.method, c.url) for c in _unowned]))
            print("[js.py DEBUG]   this_methods: " + str([m["name"] for m in scope_methods if m.get("is_this_method")]))
            method_names_set = {m["name"] for m in scope_methods}
            # Keep calls that reference a known method (scope or this)
            filtered_init_calls = [c for c in init_calls if c in method_names_set]

            ctrl = RawController(
                name=name, file=file_path, di=di,
                scope_reads=scope_reads, scope_writes=scope_writes,
                scope_methods=scope_methods, init_calls=filtered_init_calls,
                watch_depths=watch_depths, uses_compile=uses_compile,
                has_nested_scopes=has_nested_scopes,
            )

            ctrl.is_component = is_component

            raw_modules.append(ctrl)

        def _handle_directive(name: str, fn_node, file_path: str):
            has_compile   = False
            has_link      = False
            transclude    = False
            restrict      = 'EA'   # AngularJS default
            scope_bindings: dict = {}
            template_str  = None
            template_url  = None

            def scan_for_return(node):
                nonlocal has_compile, has_link, transclude, restrict, scope_bindings, template_str, template_url
                if node is None or not hasattr(node, "type"):
                    return
                if getattr(node, "type", None) == "ReturnStatement":
                    arg = getattr(node, "argument", None)
                    if arg and getattr(arg, "type", None) == "ObjectExpression":
                        for prop in getattr(arg, "properties", []) or []:
                            key = getattr(prop.key, "name", None) or getattr(prop.key, "value", None)
                            val = getattr(prop, "value", None)
                            if key == "compile":     has_compile = True
                            if key == "link":        has_link    = True
                            if key == "restrict" and getattr(val, "type", None) == "Literal":
                                restrict = str(val.value).upper()
                            if key == "template" and getattr(val, "type", None) == "Literal":
                                template_str = val.value
                            if key == "templateUrl" and getattr(val, "type", None) == "Literal":
                                template_url = val.value
                            if key == "scope" and getattr(val, "type", None) == "ObjectExpression":
                                for sp in getattr(val, "properties", []) or []:
                                    sk = getattr(sp.key, "name", None) or getattr(sp.key, "value", None)
                                    sv = getattr(sp.value, "value", None) if getattr(sp, "value", None) else None
                                    if sk and sv:
                                        scope_bindings[sk] = sv
                            if key == "transclude":
                                if getattr(val, "type", None) == "Literal" and getattr(val, "value", None) is True:
                                    transclude = True
                if getattr(node, "type", None) == "Property":
                    key = getattr(node.key, "name", None) or getattr(node.key, "value", None)
                    val = getattr(node, "value", None)
                    if key == "compile":     has_compile = True
                    if key == "link":        has_link    = True
                    if key == "restrict" and getattr(val, "type", None) == "Literal":
                        restrict = str(val.value).upper()
                    if key == "template" and getattr(val, "type", None) == "Literal":
                        template_str = val.value
                    if key == "templateUrl" and getattr(val, "type", None) == "Literal":
                        template_url = val.value
                    if key == "transclude":
                        if getattr(val, "type", None) == "Literal" and getattr(val, "value", None) is True:
                            transclude = True
                for child in iter_children(node):
                    scan_for_return(child)

            scan_for_return(fn_node)
            raw_directives.append(RawDirective(
                name=name, file=file_path,
                has_compile=has_compile, has_link=has_link, transclude=transclude,
                restrict=restrict, scope_bindings=scope_bindings,
                template=template_str, template_url=template_url,
            ))

        # ── parse each file ────────────────────────────────────────────────
        for path in paths:
            text = path.read_text(encoding="utf-8", errors="ignore")
            try:
                # range=True is needed so _fn_body_src() can slice the source
                ast = esprima.parseScript(text, tolerant=True, range=True)
            except Exception:
                continue

            # ── Pass 1: collect module aliases (var app = angular.module(...)) ──
            # Builds a map of {identifier_name: angular_module_name} for this file
            module_aliases: Dict[str, str] = {}
            _collect_module_aliases(ast, module_aliases)
            print(f"[js.py] {path.name}: module aliases = {module_aliases}")

            recurse(ast, str(path), source=text, current_owner=None,
                    module_aliases=module_aliases)

        # ── deduplicate http calls ─────────────────────────────────────────
        deduped: List[RawHttpCall] = []
        seen: Dict[tuple, int] = {}

        for call in raw_http_calls:
            sig = (call.file, call.method, call.url, getattr(call, "owner_method", None))
            if sig in seen:
                existing = deduped[seen[sig]]
                if call.owner_controller and not existing.owner_controller:
                    deduped[seen[sig]] = call
            else:
                seen[sig] = len(deduped)
                deduped.append(call)

        self.filters = raw_filters
        return raw_modules, [], [], raw_directives, deduped, raw_routes, raw_filters