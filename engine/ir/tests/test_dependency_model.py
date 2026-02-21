import pytest

from ir.dependency_model.base import DependencyType, DependencyMetadata
from ir.dependency_model.edge import DependencyEdge
from ir.dependency_model.graph import DependencyGraph


# ----------------------------
# DependencyType
# ----------------------------

def test_dependency_type_values():
    assert DependencyType.IMPORT.value == "import"
    assert DependencyType.CALL.value == "call"
    assert DependencyType.INJECT.value == "inject"
    assert DependencyType.EXTENDS.value == "extends"
    assert DependencyType.IMPLEMENTS.value == "implements"
    assert DependencyType.TEMPLATE_BINDING.value == "template_binding"


def test_dependency_type_invalid():
    with pytest.raises(ValueError):
        DependencyType("foo")


# ----------------------------
# DependencyMetadata
# ----------------------------

def test_dependency_metadata_defaults():
    m = DependencyMetadata()
    assert m.optional is False
    assert m.runtime_only is False
    assert m.notes is None


def test_dependency_metadata_custom_values():
    m = DependencyMetadata(optional=True, runtime_only=True, notes="angular only")
    assert m.optional is True
    assert m.runtime_only is True
    assert m.notes == "angular only"


def test_dependency_metadata_not_shared():
    m1 = DependencyMetadata()
    m2 = DependencyMetadata()
    m1.notes = "x"
    assert m2.notes is None


# ----------------------------
# DependencyEdge
# ----------------------------

def test_dependency_edge_creation_defaults():
    e = DependencyEdge(
        source_id="A",
        target_id="B",
        type=DependencyType.IMPORT
    )
    assert e.source_id == "A"
    assert e.target_id == "B"
    assert e.type == DependencyType.IMPORT
    assert isinstance(e.metadata, DependencyMetadata)


def test_dependency_edge_custom_metadata():
    meta = DependencyMetadata(optional=True, notes="runtime import")
    e = DependencyEdge(
        source_id="A",
        target_id="B",
        type=DependencyType.CALL,
        metadata=meta
    )
    assert e.metadata.optional is True
    assert e.metadata.notes == "runtime import"


def test_dependency_edge_empty_ids_allowed():
    e = DependencyEdge(
        source_id="",
        target_id="",
        type=DependencyType.INJECT
    )
    assert e.source_id == ""
    assert e.target_id == ""


# ----------------------------
# DependencyGraph
# ----------------------------

def test_dependency_graph_empty():
    g = DependencyGraph()
    assert g.edges == []
    assert g.outgoing("X") == []
    assert g.incoming("Y") == []
    assert g.depends_on("A", "B") is False


def test_dependency_graph_add_and_query():
    g = DependencyGraph()
    e1 = DependencyEdge("A", "B", DependencyType.IMPORT)
    e2 = DependencyEdge("A", "C", DependencyType.CALL)
    e3 = DependencyEdge("D", "A", DependencyType.INJECT)

    g.add_edge(e1)
    g.add_edge(e2)
    g.add_edge(e3)

    assert g.outgoing("A") == [e1, e2]
    assert g.incoming("A") == [e3]
    assert g.depends_on("A", "B") is True
    assert g.depends_on("A", "C") is True
    assert g.depends_on("B", "A") is False


def test_dependency_graph_self_loop():
    g = DependencyGraph()
    e = DependencyEdge("A", "A", DependencyType.EXTENDS)
    g.add_edge(e)

    assert g.depends_on("A", "A") is True
    assert g.outgoing("A") == [e]
    assert g.incoming("A") == [e]


def test_dependency_graph_duplicate_edges_allowed():
    g = DependencyGraph()
    e1 = DependencyEdge("A", "B", DependencyType.IMPORT)
    e2 = DependencyEdge("A", "B", DependencyType.IMPORT)

    g.add_edge(e1)
    g.add_edge(e2)

    assert len(g.outgoing("A")) == 2


def test_dependency_graph_large_input_fast_enough():
    g = DependencyGraph()
    for i in range(1000):
        g.add_edge(DependencyEdge(f"A{i}", f"B{i}", DependencyType.CALL))

    assert len(g.edges) == 1000
    assert g.depends_on("A500", "B500") is True
    assert g.depends_on("A9999", "B9999") is False
