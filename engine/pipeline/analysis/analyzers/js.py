from pathlib import Path
from typing import List
from .base import Analyzer

# Minimal JS AST via esprima (pip install esprima)
import esprima


class RawController:
    def __init__(self, name: str, file: str, di: List[str], scope_reads: List[str], scope_writes: List[str]):
        self.name = name
        self.file = file
        self.di = di
        self.scope_reads = scope_reads
        self.scope_writes = scope_writes

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

            # Match any `.controller('X', function(...) { ... })` in the tree
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

                        for stmt in fn_node.body.body:
                            if stmt.type == "ExpressionStatement" and stmt.expression.type == "AssignmentExpression":
                                left = stmt.expression.left
                                if (
                                    left.type == "MemberExpression"
                                    and left.object.type == "Identifier"
                                    and left.object.name == "$scope"
                                ):
                                    scope_writes.append(left.property.name)

                            if stmt.type == "ExpressionStatement" and stmt.expression.type == "CallExpression":
                                callee = stmt.expression.callee
                                if (
                                    callee.type == "MemberExpression"
                                    and callee.object.type == "Identifier"
                                    and callee.object.name == "$scope"
                                ):
                                    scope_reads.append(callee.property.name)

                        raw_modules.append(
                            RawController(
                                name=name,
                                file=file_path,
                                di=di,
                                scope_reads=scope_reads,
                                scope_writes=scope_writes,
                            )
                        )

            # Recurse through child nodes
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
