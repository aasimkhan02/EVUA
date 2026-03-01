from typing import List, Tuple, Any
from ir.code_model.module import Module
from ir.code_model.class_ import Class
from ir.code_model.function import Function
from ir.code_model.symbol import Symbol
from ir.dependency_model.graph import DependencyGraph
from ir.dependency_model.edge import DependencyEdge
from ir.template_model.template import Template
from ir.behavior_model.base import Behavior
from ir.behavior_model.side_effect import SideEffect


class IRBuilder:
    """
    Converts raw analyzer outputs into framework-agnostic IR.
    No framework logic. No heuristics. Pure normalization.
    """

    def build(self, raw_outputs: Tuple[list, list, list, list, list]):
        raw_modules, raw_templates, raw_edges, raw_directives, raw_http_calls = raw_outputs

        modules = self.build_modules(raw_modules)
        dependencies = self.build_dependencies(raw_edges)
        templates = self.build_templates(raw_templates)
        behaviors = self.build_behaviors(raw_directives)

        return modules, dependencies, templates, behaviors

    def build_modules(self, raw_modules: List) -> List[Module]:
        modules: List[Module] = []
        for rm in raw_modules:
            cls = Class(name=rm.name)

            # Propagate analyzer heuristics into IR
            cls.scope_reads = getattr(rm, "scope_reads", [])
            cls.scope_writes = getattr(rm, "scope_writes", [])
            cls.watch_depths = getattr(rm, "watch_depths", [])
            cls.uses_compile = getattr(rm, "uses_compile", False)
            cls.has_nested_scopes = getattr(rm, "has_nested_scopes", False)

            # ── DI tokens (NEW) ────────────────────────────────────────────
            # RawController.di is a list like ['$scope', '$http', '$routeParams']
            # Store it on the Class so transformation rules can generate constructors.
            cls.di = getattr(rm, "di", [])

            module = Module(
                name=rm.file,
                classes=[cls],
                functions=[],
                globals=[],
            )
            modules.append(module)
        return modules

    def build_dependencies(self, raw_edges: List) -> DependencyGraph:
        graph = DependencyGraph()
        for e in raw_edges:
            graph.add_edge(
                DependencyEdge(
                    source_id=e.source_id,
                    target_id=e.target_id,
                    type=e.type,
                    metadata=e.metadata,
                )
            )
        return graph

    def build_templates(self, raw_templates: List) -> List[Template]:
        templates: List[Template] = []
        for rt in raw_templates:
            template = Template(
                bindings=rt.bindings,
                directives=rt.directives,
            )
            templates.append(template)
        return templates

    def build_behaviors(self, raw_behaviors: List) -> List[Behavior]:
        behaviors: List[Behavior] = []
        for rb in raw_behaviors:
            if getattr(rb, "has_compile", False):
                behaviors.append(
                    SideEffect(
                        cause="directive_compile",
                        affected_symbol_id=getattr(rb, "name", "unknown"),
                        description="AngularJS directive uses compile()",
                    )
                )
            if getattr(rb, "has_link", False):
                behaviors.append(
                    SideEffect(
                        cause="directive_link",
                        affected_symbol_id=getattr(rb, "name", "unknown"),
                        description="AngularJS directive uses link()",
                    )
                )
            if getattr(rb, "transclude", False):
                behaviors.append(
                    SideEffect(
                        cause="directive_transclusion",
                        affected_symbol_id=getattr(rb, "name", "unknown"),
                        description="AngularJS directive uses transclusion",
                    )
                )
        return behaviors

    def _build_class(self, rc) -> Class:
        return Class(
            name=rc.name,
            fields=[self._build_symbol(s) for s in getattr(rc, "fields", [])],
            methods=[self._build_function(f) for f in getattr(rc, "methods", [])],
        )

    def _build_function(self, rf) -> Function:
        return Function(
            name=rf.name,
            parameters=[self._build_symbol(p) for p in getattr(rf, "parameters", [])],
            returns=getattr(rf, "returns", None),
            body_refs=getattr(rf, "body_refs", []),
        )

    def _build_symbol(self, rs) -> Symbol:
        return Symbol(
            name=rs.name,
            type_hint=getattr(rs, "type_hint", None),
            mutable=getattr(rs, "mutable", True),
        )