"""
pipeline/transformation/helpers.py

Canonical iterators for transformation rules.
Written against the REAL IR types:
  - ir.code_model.module.Module       (.name, .classes)   -- NOTE: .name not .path
  - ir.code_model.class_.Class        (.id, .name)
  - ir.behavior_model.observer.Observer (.id, .observed_symbol_id, .trigger) -- NOTE: no .name
  - ir.migration_model.base.ChangeSource  (RULE / AI / HUMAN)

HttpCall is NOT an IR type — it lives in the analysis layer.
"""

from typing import Iterator, Any
from pipeline.patterns.roles import SemanticRole


def iter_nodes_with_role(analysis, patterns, role: SemanticRole) -> Iterator[Any]:
    seen = set()
    roles_by_node = getattr(patterns, "roles_by_node", {})

    for node_id, roles in roles_by_node.items():
        if role in roles:
            node = _find_node(analysis, node_id)
            if node is not None:
                nid = getattr(node, "id", node_id)
                if nid not in seen:
                    seen.add(nid)
                    yield node

    for item in getattr(patterns, "matched_patterns", []):
        try:
            node, item_role, _conf = item
        except (TypeError, ValueError):
            continue
        if item_role == role:
            nid = getattr(node, "id", id(node))
            if nid not in seen:
                seen.add(nid)
                yield node


def iter_controllers(analysis, patterns) -> Iterator[Any]:
    """
    Yields ir.code_model.class_.Class nodes that are controllers.
    IR Class has: .id (uuid str), .name (str), .fields, .methods
    """
    seen = set()

    for node in iter_nodes_with_role(analysis, patterns, SemanticRole.CONTROLLER):
        seen.add(node.id)
        yield node

    # Name fallback — Module.classes, Module.name (NOT .path)
    for m in getattr(analysis, "modules", []):
        for c in getattr(m, "classes", []):
            if c.id in seen:
                continue
            if c.name.lower().endswith(("controller", "ctrl")):
                seen.add(c.id)
                yield c


def iter_services(analysis, patterns) -> Iterator[Any]:
    """
    Yields ir.code_model.class_.Class nodes that are services.
    """
    seen = set()

    for node in iter_nodes_with_role(analysis, patterns, SemanticRole.SERVICE):
        seen.add(node.id)
        yield node

    for m in getattr(analysis, "modules", []):
        for c in getattr(m, "classes", []):
            if c.id in seen:
                continue
            if c.name.lower().endswith(("service", "svc")):
                seen.add(c.id)
                yield c


def iter_http_calls(analysis, patterns) -> Iterator[Any]:
    """
    Yields HTTP call objects from the analysis layer (NOT an IR type).
    Expected attributes: .id, .file, .method, .url
    Falls back to analysis.http_calls directly.
    """
    seen = set()

    for node in iter_nodes_with_role(analysis, patterns, SemanticRole.HTTP_CALL):
        seen.add(getattr(node, "id", id(node)))
        yield node

    for call in getattr(analysis, "http_calls", []):
        cid = getattr(call, "id", id(call))
        if cid not in seen:
            seen.add(cid)
            yield call


def iter_shallow_watches(analysis, patterns) -> Iterator[Any]:
    """
    Yields ir.behavior_model.observer.Observer nodes.
    Observer has: .id, .observed_symbol_id, .trigger, .description
    IMPORTANT: Observer has NO .name — use observed_symbol_id instead.
    Use resolve_owner_class() to find the Class that owns this observer.
    """
    seen = set()

    for node in iter_nodes_with_role(analysis, patterns, SemanticRole.SHALLOW_WATCH):
        seen.add(getattr(node, "id", id(node)))
        yield node

    for watch in getattr(analysis, "watches", []):
        wid = getattr(watch, "id", id(watch))
        if wid not in seen:
            seen.add(wid)
            yield watch


def resolve_owner_class(analysis, node_id: str):
    """
    Find the Class that owns a given node_id.
    Checks class id itself, then methods and fields.
    Returns ir.code_model.class_.Class or None.
    """
    for m in getattr(analysis, "modules", []):
        for c in getattr(m, "classes", []):
            if c.id == node_id:
                return c
            for method in getattr(c, "methods", []):
                if getattr(method, "id", None) == node_id:
                    return c
            for field_ in getattr(c, "fields", []):
                if getattr(field_, "id", None) == node_id:
                    return c
    return None


def _find_node(analysis, node_id: str):
    for m in getattr(analysis, "modules", []):
        for c in getattr(m, "classes", []):
            if c.id == node_id:
                return c
    for call in getattr(analysis, "http_calls", []):
        if getattr(call, "id", None) == node_id:
            return call
    for watch in getattr(analysis, "watches", []):
        if getattr(watch, "id", None) == node_id:
            return watch
    return None