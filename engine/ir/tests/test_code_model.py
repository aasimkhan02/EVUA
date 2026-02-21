import pytest
import uuid

from ir.code_model.base import IRNode, SourceLocation
from ir.code_model.symbol import Symbol
from ir.code_model.function import Function
from ir.code_model.class_ import Class
from ir.code_model.module import Module


# ----------------------------
# IRNode & SourceLocation
# ----------------------------

def test_irnode_auto_id():
    n1 = IRNode()
    n2 = IRNode()

    assert n1.id != n2.id
    uuid.UUID(n1.id)
    uuid.UUID(n2.id)


def test_irnode_defaults():
    node = IRNode()
    assert node.location is None
    assert node.metadata == {}
    assert isinstance(node.metadata, dict)


def test_irnode_metadata_not_shared():
    a = IRNode()
    b = IRNode()
    a.metadata["x"] = "1"
    assert b.metadata == {}


def test_source_location_fields():
    loc = SourceLocation(file="a.js", line_start=1, line_end=10)
    assert loc.file == "a.js"
    assert loc.line_start == 1
    assert loc.line_end == 10


def test_source_location_weird_ranges_allowed():
    loc = SourceLocation(file="a.js", line_start=10, line_end=1)
    assert loc.line_start == 10
    assert loc.line_end == 1


# ----------------------------
# Symbol
# ----------------------------

def test_symbol_creation_minimal():
    s = Symbol(name="x")
    assert s.name == "x"
    assert s.type_hint is None
    assert s.mutable is True


def test_symbol_full_fields():
    s = Symbol(name="count", type_hint="number", mutable=False)
    assert s.name == "count"
    assert s.type_hint == "number"
    assert s.mutable is False


def test_symbol_is_irnode():
    s = Symbol(name="x")
    assert isinstance(s, IRNode)


# ----------------------------
# Function
# ----------------------------

def test_function_creation_minimal():
    p1 = Symbol(name="a")
    fn = Function(name="f", parameters=[p1])
    assert fn.name == "f"
    assert fn.parameters == [p1]
    assert fn.returns is None
    assert fn.body_refs == []


def test_function_body_refs_isolated():
    f1 = Function(name="a", parameters=[])
    f2 = Function(name="b", parameters=[])

    f1.body_refs.append("x")
    assert f2.body_refs == []


def test_function_is_irnode():
    fn = Function(name="f", parameters=[])
    assert isinstance(fn, IRNode)


def test_function_missing_required_fields():
    with pytest.raises(TypeError):
        Function(parameters=[])


# ----------------------------
# Class
# ----------------------------

def test_class_creation_minimal():
    c = Class(name="A")
    assert c.name == "A"
    assert c.fields == []
    assert c.methods == []


def test_class_fields_methods_isolated():
    c1 = Class(name="A")
    c2 = Class(name="B")

    c1.fields.append(Symbol(name="x"))
    assert c2.fields == []


def test_class_is_irnode():
    c = Class(name="A")
    assert isinstance(c, IRNode)


def test_class_missing_name_fails():
    with pytest.raises(TypeError):
        Class()


# ----------------------------
# Module
# ----------------------------

def test_module_creation_minimal():
    m = Module(name="mod")
    assert m.name == "mod"
    assert m.classes == []
    assert m.functions == []
    assert m.globals == []


def test_module_is_irnode():
    m = Module(name="m")
    assert isinstance(m, IRNode)


def test_module_lists_isolated():
    m1 = Module(name="a")
    m2 = Module(name="b")

    m1.classes.append(Class(name="C"))
    assert m2.classes == []


def test_module_missing_name_fails():
    with pytest.raises(TypeError):
        Module()


# ----------------------------
# Cross-invariants
# ----------------------------

@pytest.mark.parametrize("obj", [
    Symbol(name="x"),
    Function(name="f", parameters=[]),
    Class(name="C"),
    Module(name="M"),
])
def test_all_code_models_are_irnodes(obj):
    assert isinstance(obj, IRNode)
