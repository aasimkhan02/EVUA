from pathlib import Path
from typing import List, Dict
from .base import Analyzer
import esprima


class RawController:
    def __init__(
        self,
        name: str,
        file: str,
        di: List[str],
        scope_reads: List[str],
        scope_writes: List[str],
        watch_depths: List[str],  # "shallow" | "deep"
        uses_compile: bool = False,
        has_nested_scopes: bool = False,
    ):
        self.name = name
        self.file = file
        self.di = di
        self.scope_reads = scope_reads
        self.scope_writes = scope_writes
        self.watch_depths = watch_depths
        self.uses_compile = uses_compile
        self.has_nested_scopes = has_nested_scopes

        # IRBuilder expects these
        self.classes = []
        self.functions = []
        self.globals = []


class RawDirective:
    def __init__(
        self,
        name: str,
        file: str,
        has_compile: bool,
        has_link: bool,
        transclude: bool,
    ):
        self.name = name
        self.file = file
        self.has_compile = has_compile
        self.has_link = has_link
        self.transclude = transclude

        # IRBuilder expects these
        self.classes = []
        self.functions = []
        self.globals = []

class RawHttpCall:
    def __init__(self, file: str, method: str, url: str | None, uses_q: bool):
        self.file = file
        self.method = method  # get/post/put/delete/config/q_all/q_defer
        self.url = url
        self.uses_q = uses_q

        # IRBuilder expects these
        self.classes = []
        self.functions = []
        self.globals = []

def _is_identifier(node, name):
    return node is not None and getattr(node, "type", None) == "Identifier" and getattr(node, "name", None) == name


def _member_object_name(member_node):
    """
    Given a MemberExpression, attempt to return the "object" identifier name if simple.
    Works for $scope.x or this.something.
    """
    if not member_node or getattr(member_node, "type", None) != "MemberExpression":
        return None
    obj = getattr(member_node, "object", None)
    if getattr(obj, "type", None) == "Identifier":
        return obj.name
    return None


class JSAnalyzer(Analyzer):
    def analyze(self, paths: List[Path]):
        raw_modules: List[RawController] = []
        raw_directives: List[RawDirective] = []
        raw_http_calls: List[RawHttpCall] = []


        def recurse(node, file_path: str, ctx: Dict = None):
            """
            Generic recursive walker that yields nothing but allows us to inspect every node.
            """
            if node is None or not hasattr(node, "type"):
                return

            # Detect controller calls anywhere (chained or not):
            if node.type == "CallExpression":
                callee = getattr(node, "callee", None)
                if getattr(callee, "type", None) == "MemberExpression":
                    prop = getattr(callee.property, "name", None)
                    if prop == "controller":
                        # controller(name, fn)
                        args = getattr(node, "arguments", []) or []
                        if len(args) >= 2:
                            name_node = args[0]
                            fn_node = args[1]
                            if getattr(name_node, "type", None) == "Literal" and getattr(fn_node, "type", None) in ("FunctionExpression", "ArrowFunctionExpression"):
                                _handle_controller(name_node.value, fn_node, file_path)

                    if prop == "directive":
                        args = getattr(node, "arguments", []) or []
                        if len(args) >= 2:
                            name_node = args[0]
                            fn_node = args[1]
                            # directive(name, function() { return {...}; }) OR factory function
                            if getattr(name_node, "type", None) == "Literal" and getattr(fn_node, "type", None) in ("FunctionExpression", "ArrowFunctionExpression"):
                                _handle_directive(name_node.value, fn_node, file_path)

                    # --- $http detection ---
                    if getattr(callee, "type", None) == "MemberExpression":
                        obj = getattr(callee.object, "type", None) == "Identifier" and getattr(callee.object, "name", None)
                        prop = getattr(callee.property, "name", None)
                        if obj == "$http" and prop in ("get", "post", "put", "delete"):
                            args = getattr(node, "arguments", []) or []
                            url = None
                            if args and getattr(args[0], "type", None) == "Literal":
                                url = args[0].value
                            raw_http_calls.append(RawHttpCall(file_path, prop, url, uses_q=False))

                    # --- $http({ config }) ---
                    if getattr(callee, "type", None) == "Identifier" and getattr(callee, "name", None) == "$http":
                        raw_http_calls.append(RawHttpCall(file_path, "config", None, uses_q=False))

                    # --- $q detection ---
                    if getattr(callee, "type", None) == "MemberExpression":
                        obj = getattr(callee.object, "type", None) == "Identifier" and getattr(callee.object, "name", None)
                        prop = getattr(callee.property, "name", None)
                        if obj == "$q" and prop in ("all", "defer"):
                            raw_http_calls.append(RawHttpCall(file_path, f"q_{prop}", None, uses_q=True))

            # Recurse into all child nodes (lists + single nodes)
            for attr in dir(node):
                if attr.startswith("_"):
                    continue
                try:
                    child = getattr(node, attr)
                except Exception:
                    continue
                if isinstance(child, list):
                    for c in child:
                        if hasattr(c, "type"):
                            recurse(c, file_path, ctx)
                elif hasattr(child, "type"):
                    recurse(child, file_path, ctx)

        def _handle_controller(name: str, fn_node, file_path: str):
            """
            Scan the controller function node thoroughly to find $scope mutations, watches, $compile, $new, etc.
            """
            di = []
            for p in getattr(fn_node, "params", []) or []:
                if getattr(p, "type", None) == "Identifier":
                    di.append(p.name)

            scope_reads: List[str] = []
            scope_writes: List[str] = []
            watch_depths: List[str] = []
            uses_compile = False
            has_nested_scopes = False

            # inner recursive scanner for the function body
            def scan_fn(node):
                nonlocal uses_compile, has_nested_scopes
                if node is None or not hasattr(node, "type"):
                    return

                # Assignment to $scope.something
                if getattr(node, "type", None) == "AssignmentExpression":
                    left = getattr(node, "left", None)
                    if getattr(left, "type", None) == "MemberExpression":
                        obj = getattr(left, "object", None)
                        prop = getattr(left, "property", None)
                        if getattr(obj, "type", None) == "Identifier" and getattr(obj, "name", None) == "$scope":
                            # property can be Identifier or Literal
                            pname = getattr(prop, "name", None) or getattr(prop, "value", None)
                            if pname:
                                scope_writes.append(pname)

                # Variable declarator: var child = $scope.$new(); or var x = $compile(el)($scope);
                if getattr(node, "type", None) == "VariableDeclarator":
                    init = getattr(node, "init", None)
                    if init:
                        # $scope.$new()
                        if getattr(init, "type", None) == "CallExpression":
                            callee = getattr(init, "callee", None)
                            if getattr(callee, "type", None) == "MemberExpression":
                                obj = getattr(callee.object, "type", None) == "Identifier" and getattr(callee.object, "name", None)
                                prop_name = getattr(callee.property, "name", None)
                                if obj == "$scope" and prop_name == "$new":
                                    has_nested_scopes = True
                            # $compile(...) returns function which can be immediately called; handled below as generic call
                        # handle nested further
                        scan_fn(init)

                # Calls: $scope.$watch, $compile, $scope.$new anywhere
                if getattr(node, "type", None) == "CallExpression":
                    callee = getattr(node, "callee", None)

                    # $scope.$watch(...)
                    if getattr(callee, "type", None) == "MemberExpression":
                        obj = getattr(callee.object, "type", None)
                        if obj == "Identifier" and getattr(callee.object, "name", None) == "$scope":
                            pname = getattr(callee.property, "name", None)
                            if pname == "$watch":
                                args = getattr(node, "arguments", []) or []
                                is_deep = False

                                # $scope.$watch(expr, fn, true) → deep
                                if len(args) >= 3:
                                    third = args[2]
                                    if getattr(third, "type", None) == "Literal" and getattr(third, "value", None) is True:
                                        is_deep = True

                                if is_deep:
                                    watch_depths.append("deep")
                                else:
                                    watch_depths.append("shallow")


                            if pname == "$new":
                                has_nested_scopes = True

                    # $compile(...)
                    if getattr(callee, "type", None) == "Identifier" and getattr(callee, "name", None) == "$compile":
                        uses_compile = True

                    # also handle case: ($compile(el)($scope)) pattern where call is nested; scanning child nodes will catch inner callee too

                # MemberExpression access that might read $scope.something
                if getattr(node, "type", None) == "MemberExpression":
                    obj = getattr(node, "object", None)
                    if getattr(obj, "type", None) == "Identifier" and getattr(obj, "name", None) == "$scope":
                        prop = getattr(node, "property", None)
                        pname = getattr(prop, "name", None) or getattr(prop, "value", None)
                        if pname:
                            scope_reads.append(pname)

                # Recurse children
                for attr in dir(node):
                    if attr.startswith("_"):
                        continue
                    try:
                        child = getattr(node, attr)
                    except Exception:
                        continue
                    if isinstance(child, list):
                        for c in child:
                            if hasattr(c, "type"):
                                scan_fn(c)
                    elif hasattr(child, "type"):
                        scan_fn(child)

            # start scan on function body (handles both FunctionExpression and Arrow)
            body = getattr(fn_node, "body", None)
            if body:
                # body could be BlockStatement with .body list
                scan_fn(body)

            raw_modules.append(
                RawController(
                    name=name,
                    file=file_path,
                    di=di,
                    scope_reads=scope_reads,
                    scope_writes=scope_writes,
                    watch_depths=watch_depths,
                    uses_compile=uses_compile,
                    has_nested_scopes=has_nested_scopes,
                )
            )

        def _handle_directive(name: str, fn_node, file_path: str):
            """
            Scan directive factory function for compile/link/transclude flags. The directive may return
            an object expression or construct complex logic; we try to find returned ObjectExpression.
            """
            has_compile = False
            has_link = False
            transclude = False

            # recursively scan to find ReturnStatement whose argument is ObjectExpression
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
                                if getattr(val, "type", None) == "Literal" and getattr(val, "value", None) is True:
                                    transclude = True

                # also detect compile/link as functions defined inside and later referenced; a conservative approach:
                if getattr(node, "type", None) == "Property":
                    key = getattr(node.key, "name", None) or getattr(node.key, "value", None)
                    if key == "compile":
                        has_compile = True
                    if key == "link":
                        has_link = True
                    if key == "transclude":
                        val = getattr(node, "value", None)
                        if getattr(val, "type", None) == "Literal" and getattr(val, "value", None) is True:
                            transclude = True

                # Recurse
                for attr in dir(node):
                    if attr.startswith("_"):
                        continue
                    try:
                        child = getattr(node, attr)
                    except Exception:
                        continue
                    if isinstance(child, list):
                        for c in child:
                            if hasattr(c, "type"):
                                scan_for_return(c)
                    elif hasattr(child, "type"):
                        scan_for_return(child)

            scan_for_return(fn_node)

            raw_directives.append(
                RawDirective(
                    name=name,
                    file=file_path,
                    has_compile=has_compile,
                    has_link=has_link,
                    transclude=transclude,
                )
            )

        # Entry: parse each file and recurse entire AST
        for path in paths:
            text = path.read_text(encoding="utf-8", errors="ignore")
            try:
                ast = esprima.parseScript(text, tolerant=True)
            except Exception:
                continue
            recurse(ast, str(path))

        # Return: raw_modules (controllers), raw_templates (none here), raw_dependencies (none), raw_directives
        return raw_modules, [], [], raw_directives, raw_http_calls

