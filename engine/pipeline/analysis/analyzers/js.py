from pathlib import Path
from typing import List, Dict
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
    def __init__(self, file: str, method: str, url, uses_q: bool):
        self.id = str(uuid.uuid4())
        self.file = file
        self.method = method
        self.url = url
        self.uses_q = uses_q

        self.classes = []
        self.functions = []
        self.globals = []


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
    AngularJS supports two DI syntaxes:

    1. Plain function:
       .controller('Name', function($scope) { ... })

    2. DI array (minification-safe):
       .controller('Name', ['$scope', '$http', function($scope, $http) { ... }])

    This function normalises both and always returns the FunctionExpression node,
    or None if neither pattern is matched.
    """
    if arg_node is None:
        return None

    t = getattr(arg_node, "type", None)

    # Plain function — already what we want
    if t in ("FunctionExpression", "ArrowFunctionExpression"):
        return arg_node

    # DI array — last element must be the function
    if t == "ArrayExpression":
        elements = getattr(arg_node, "elements", []) or []
        if elements:
            last = elements[-1]
            if getattr(last, "type", None) in ("FunctionExpression", "ArrowFunctionExpression"):
                return last

    return None


def _extract_di_names(arg_node) -> List[str]:
    """
    Extract DI token names from either syntax.

    Plain function  → read parameter names from function params
    DI array        → read string literals from the array (more reliable for minified code)
    """
    if arg_node is None:
        return []

    t = getattr(arg_node, "type", None)

    if t == "ArrayExpression":
        names = []
        elements = getattr(arg_node, "elements", []) or []
        for el in elements:
            if getattr(el, "type", None) == "Literal":
                names.append(el.value)
        return names

    if t in ("FunctionExpression", "ArrowFunctionExpression"):
        names = []
        for p in getattr(arg_node, "params", []) or []:
            if getattr(p, "type", None) == "Identifier":
                names.append(p.name)
        return names

    return []


class JSAnalyzer(Analyzer):
    def analyze(self, paths: List[Path]):
        raw_modules: List[RawController] = []
        raw_directives: List[RawDirective] = []
        raw_http_calls: List[RawHttpCall] = []

        def recurse(node, file_path: str, ctx: Dict = None):
            if node is None or not hasattr(node, "type"):
                return

            if node.type == "CallExpression":
                callee = getattr(node, "callee", None)
                args   = getattr(node, "arguments", []) or []

                if getattr(callee, "type", None) == "MemberExpression":
                    prop = getattr(callee.property, "name", None)

                    # .controller('Name', fn | ['$dep', fn])
                    if prop == "controller" and len(args) >= 2:
                        name_node = args[0]
                        fn_node   = _extract_fn_from_arg(args[1])
                        if (
                            getattr(name_node, "type", None) == "Literal"
                            and fn_node is not None
                        ):
                            _handle_controller(name_node.value, args[1], fn_node, file_path)

                    # .directive('Name', fn | ['$dep', fn])
                    elif prop == "directive" and len(args) >= 2:
                        name_node = args[0]
                        fn_node   = _extract_fn_from_arg(args[1])
                        if (
                            getattr(name_node, "type", None) == "Literal"
                            and fn_node is not None
                        ):
                            _handle_directive(name_node.value, fn_node, file_path)

                    # .service('Name', fn | ['$dep', fn])
                    elif prop == "service" and len(args) >= 2:
                        name_node = args[0]
                        fn_node   = _extract_fn_from_arg(args[1])
                        if (
                            getattr(name_node, "type", None) == "Literal"
                            and fn_node is not None
                        ):
                            _handle_controller(name_node.value, args[1], fn_node, file_path)

                    # .factory('Name', fn | ['$dep', fn])
                    elif prop == "factory" and len(args) >= 2:
                        name_node = args[0]
                        fn_node   = _extract_fn_from_arg(args[1])
                        if (
                            getattr(name_node, "type", None) == "Literal"
                            and fn_node is not None
                        ):
                            _handle_controller(name_node.value, args[1], fn_node, file_path)

                    # $http.get / .post / .put / .delete
                    obj_name = (
                        getattr(callee.object, "name", None)
                        if getattr(callee.object, "type", None) == "Identifier"
                        else None
                    )
                    if obj_name == "$http" and prop in ("get", "post", "put", "delete"):
                        url = None
                        if args and getattr(args[0], "type", None) == "Literal":
                            url = args[0].value
                        raw_http_calls.append(RawHttpCall(file_path, prop, url, uses_q=False))

                    # $q.all / $q.defer
                    if obj_name == "$q" and prop in ("all", "defer"):
                        raw_http_calls.append(RawHttpCall(file_path, f"q_{prop}", None, uses_q=True))

                # $http({ config })
                if (
                    getattr(callee, "type", None) == "Identifier"
                    and getattr(callee, "name", None) == "$http"
                ):
                    raw_http_calls.append(RawHttpCall(file_path, "config", None, uses_q=False))

            for child in iter_children(node):
                recurse(child, file_path, ctx)

        def _handle_controller(name: str, raw_arg, fn_node, file_path: str):
            di = _extract_di_names(raw_arg)

            scope_reads: List[str]  = []
            scope_writes: List[str] = []
            watch_depths: List[str] = []
            uses_compile     = False
            has_nested_scopes = False

            def scan_fn(node):
                nonlocal uses_compile, has_nested_scopes
                if node is None or not hasattr(node, "type"):
                    return

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

                if getattr(node, "type", None) == "VariableDeclarator":
                    init = getattr(node, "init", None)
                    if init:
                        if getattr(init, "type", None) == "CallExpression":
                            callee = getattr(init, "callee", None)
                            if getattr(callee, "type", None) == "MemberExpression":
                                if (
                                    getattr(callee.object, "type", None) == "Identifier"
                                    and getattr(callee.object, "name", None) == "$scope"
                                    and getattr(callee.property, "name", None) == "$new"
                                ):
                                    has_nested_scopes = True
                        scan_fn(init)

                if getattr(node, "type", None) == "CallExpression":
                    callee = getattr(node, "callee", None)

                    if getattr(callee, "type", None) == "MemberExpression":
                        obj_type = getattr(callee.object, "type", None)
                        obj_name = getattr(callee.object, "name", None) if obj_type == "Identifier" else None
                        pname    = getattr(callee.property, "name", None)

                        if obj_name == "$scope":
                            if pname == "$watch":
                                call_args = getattr(node, "arguments", []) or []
                                is_deep   = False
                                if len(call_args) >= 3:
                                    third = call_args[2]
                                    if (
                                        getattr(third, "type", None) == "Literal"
                                        and getattr(third, "value", None) is True
                                    ):
                                        is_deep = True
                                watch_depths.append("deep" if is_deep else "shallow")

                            if pname == "$new":
                                has_nested_scopes = True

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
                            if key == "compile":
                                has_compile = True
                            if key == "link":
                                has_link = True
                            if key == "transclude":
                                if (
                                    getattr(val, "type", None) == "Literal"
                                    and getattr(val, "value", None) is True
                                ):
                                    transclude = True

                if getattr(node, "type", None) == "Property":
                    key = getattr(node.key, "name", None) or getattr(node.key, "value", None)
                    if key == "compile":
                        has_compile = True
                    if key == "link":
                        has_link = True
                    if key == "transclude":
                        val = getattr(node, "value", None)
                        if (
                            getattr(val, "type", None) == "Literal"
                            and getattr(val, "value", None) is True
                        ):
                            transclude = True

                for child in iter_children(node):
                    scan_for_return(child)

            scan_for_return(fn_node)

            raw_directives.append(RawDirective(
                name=name,
                file=file_path,
                has_compile=has_compile,
                has_link=has_link,
                transclude=transclude,
            ))

        for path in paths:
            text = path.read_text(encoding="utf-8", errors="ignore")
            try:
                ast = esprima.parseScript(text, tolerant=True)
            except Exception:
                continue
            recurse(ast, str(path))

        return raw_modules, [], [], raw_directives, raw_http_calls