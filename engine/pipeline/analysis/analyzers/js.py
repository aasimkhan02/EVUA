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
    ):
        self.name = name
        self.file = file
        self.di = di
        self.scope_reads = scope_reads
        self.scope_writes = scope_writes
        self.watch_depths = watch_depths

        # IRBuilder expects these
        self.classes = []
        self.functions = []
        self.globals = []


class JSAnalyzer(Analyzer):
    def analyze(self, paths: List[Path]):
        raw_modules = []

        def walk(node, file_path: str):
            if not hasattr(node, "type"):
                return

            # Match angular.module(...).controller('X', function(...) { ... })
            if (
                node.type == "CallExpression"
                and node.callee.type == "MemberExpression"
                and getattr(node.callee.property, "name", None) == "controller"
            ):
                args = node.arguments
                if len(args) >= 2:
                    name_node = args[0]
                    fn_node = args[1]

                    if name_node.type == "Literal" and fn_node.type == "FunctionExpression":
                        name = name_node.value
                        di = [p.name for p in fn_node.params]

                        scope_reads: List[str] = []
                        scope_writes: List[str] = []
                        watch_depths: List[str] = []

                        for stmt in fn_node.body.body:
                            # $scope.x = ...
                            if stmt.type == "ExpressionStatement" and stmt.expression.type == "AssignmentExpression":
                                left = stmt.expression.left
                                if (
                                    left.type == "MemberExpression"
                                    and left.object.type == "Identifier"
                                    and left.object.name == "$scope"
                                ):
                                    scope_writes.append(left.property.name)

                            # $scope.$watch('x', fn, true)
                            if stmt.type == "ExpressionStatement" and stmt.expression.type == "CallExpression":
                                callee = stmt.expression.callee
                                if (
                                    callee.type == "MemberExpression"
                                    and callee.object.type == "Identifier"
                                    and callee.object.name == "$scope"
                                    and getattr(callee.property, "name", None) == "$watch"
                                ):
                                    # Third argument true → deep watch
                                    if len(stmt.expression.arguments) >= 3:
                                        third = stmt.expression.arguments[2]
                                        if third.type == "Literal" and third.value is True:
                                            watch_depths.append("deep")
                                        else:
                                            watch_depths.append("shallow")
                                    else:
                                        watch_depths.append("shallow")

                        raw_modules.append(
                            RawController(
                                name=name,
                                file=file_path,
                                di=di,
                                scope_reads=scope_reads,
                                scope_writes=scope_writes,
                                watch_depths=watch_depths,
                            )
                        )

            for attr in dir(node):
                child = getattr(node, attr)
                if isinstance(child, list):
                    for c in child:
                        if hasattr(c, "type"):
                            walk(c, file_path)
                elif hasattr(child, "type"):
                    walk(child, file_path)

        for path in paths:
            text = path.read_text(encoding="utf-8", errors="ignore")
            try:
                ast = esprima.parseScript(text, tolerant=True)
            except Exception:
                continue
            walk(ast, str(path))

        return raw_modules, [], [], []
