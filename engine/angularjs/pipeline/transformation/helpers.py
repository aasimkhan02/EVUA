"""
pipeline/transformation/helpers.py
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


def _is_angularjs_component_name(name: str) -> bool:
    """
    Return True if *name* looks like an AngularJS 1.5+ .component() registration.

    AngularJS .component() names are always camelCase (start with a lowercase
    letter), while classic controllers (FooController), services (FooService),
    and factories (FooFactory) all start with an uppercase letter.

    This heuristic catches cases where the IR conversion drops the is_component
    flag that js.py sets on RawController objects.

    Examples that return True:  'userProfile', 'phoneList', 'phoneDetail'
    Examples that return False: 'UserListController', 'AuthService', 'PhoneService'
    """
    if not name:
        return False
    # Must start lowercase (camelCase component names)
    if not name[0].islower():
        return False
    # Exclude anything that looks like a service (shouldn't happen with lowercase
    # start, but be defensive)
    lower = name.lower()
    if lower.endswith(("service", "svc", "factory", "provider", "filter")):
        return False
    return True


def iter_controllers(analysis, patterns) -> Iterator[Any]:
    """
    Yields RawController nodes that are controllers or .component() registrations.

    Four cases:
      1. SemanticRole.CONTROLLER assigned by pattern detectors
      2. Name ends in 'Controller' or 'Ctrl' (classic AngularJS style)
      3. is_component=True — registered via .component() by js.py; name does NOT
         end in Controller (e.g. 'userProfile', 'phoneList', 'phoneDetail')
      4. Name is camelCase (starts lowercase) — fallback for when the IR conversion
         drops the is_component attribute; covers alias-based app.component('x'),
         chained angular.module('x').component('y'), and self/vm-alias controllers.
    """
    seen = set()

    for node in iter_nodes_with_role(analysis, patterns, SemanticRole.CONTROLLER):
        seen.add(node.id)
        yield node

    for m in getattr(analysis, "modules", []):
        for c in getattr(m, "classes", []):
            if c.id in seen:
                continue

            # Classic Controller/Ctrl suffix
            if c.name.lower().endswith(("controller", "ctrl")):
                print(f"[helpers] iter_controllers: yielding classic controller '{c.name}'")
                seen.add(c.id)
                yield c
                continue

            # AngularJS .component() — is_component=True set by js.py (when preserved by IR)
            if getattr(c, "is_component", False):
                print(f"[helpers] iter_controllers: yielding .component() entry (is_component) '{c.name}'")
                c.is_component = True   # 🔥 FORCE PRESERVE
                seen.add(c.id)
                yield c
                continue
            # Fallback: camelCase name signals an AngularJS 1.5+ .component() registration.
            # Classic controllers and services always use PascalCase; .component() names
            # use camelCase (e.g. userProfile, phoneList, phoneDetail).
            # This handles cases where the IR conversion drops is_component.
            if _is_angularjs_component_name(c.name):
                print(f"[helpers] iter_controllers: yielding .component() entry (camelCase) '{c.name}'")
                c.is_component = True   # 🔥 CRITICAL FIX
                seen.add(c.id)
                yield c
            else:
                print(f"[helpers] iter_controllers: SKIPPING '{c.name}' (not controller, not component)")

def iter_services(analysis, patterns) -> Iterator[Any]:
    """
    Yields ir.code_model.class_.Class nodes that are services.
    Excludes .component() registrations (is_component=True) which belong to iter_controllers.
    """
    seen = set()

    for node in iter_nodes_with_role(analysis, patterns, SemanticRole.SERVICE):
        seen.add(node.id)
        yield node

    for m in getattr(analysis, "modules", []):
        for c in getattr(m, "classes", []):
            if c.id in seen:
                continue
            if getattr(c, "is_component", False):
                print(f"[helpers] iter_services: SKIPPING '{c.name}' (is_component=True, belongs to iter_controllers)")
                continue
            # Also skip camelCase names — those are .component() registrations,
            # even when the IR drops the is_component flag.
            if _is_angularjs_component_name(c.name):
                print(f"[helpers] iter_services: SKIPPING '{c.name}' (camelCase .component(), belongs to iter_controllers)")
                continue
            if c.name.lower().endswith(("service", "svc")):
                print(f"[helpers] iter_services: yielding service '{c.name}'")
                seen.add(c.id)
                yield c


def iter_http_calls(analysis, patterns) -> Iterator[Any]:
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