from typing import List
from ir.code_model.module import Module
from ir.code_model.class_ import Class
from ir.code_model.function import Function
from ir.code_model.symbol import Symbol
from ir.dependency_model.graph import DependencyGraph
from ir.dependency_model.edge import DependencyEdge
from ir.template_model.template import Template
from ir.behavior_model.base import Behavior


class IRBuilder:
    """
    Converts raw analyzer outputs into framework-agnostic IR.
    No framework logic. No heuristics. Pure normalization.
    """

    def build_modules(self, raw_modules: List) -> List[Module]:
        modules: List[Module] = []
        for rm in raw_modules:
            cls = Class(name=rm.name)

            # 🔥 Propagate analyzer heuristics into IR
            cls.scope_reads = getattr(rm, "scope_reads", [])
            cls.scope_writes = getattr(rm, "scope_writes", [])
            cls.watch_depths = getattr(rm, "watch_depths", [])

            module = Module(
                name=rm.file,
                classes=[cls],   # controller → class
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
        return list(raw_behaviors)

    # Keeping these helpers for future non-Angular analyzers
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
