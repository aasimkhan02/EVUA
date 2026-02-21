import pytest
import uuid

from ir.template_model.base import TemplateNode
from ir.template_model.binding import Binding, BindingType
from ir.template_model.directive import Directive, DirectiveType
from ir.template_model.template import Template
from ir.code_model.base import IRNode


# ----------------------------
# TemplateNode
# ----------------------------

def test_template_node_defaults():
    t = TemplateNode()
    assert t.name is None
    assert isinstance(t, IRNode)
    uuid.UUID(t.id)


def test_template_node_name():
    t = TemplateNode(name="div")
    assert t.name == "div"


# ----------------------------
# BindingType
# ----------------------------

def test_binding_type_values():
    assert BindingType.READ.value == "read"
    assert BindingType.WRITE.value == "write"
    assert BindingType.TWO_WAY.value == "two_way"


def test_binding_type_invalid():
    with pytest.raises(ValueError):
        BindingType("mutate")


# ----------------------------
# Binding
# ----------------------------

def test_binding_creation():
    b = Binding(
        expression="user.name",
        target_symbol="sym1",
        binding_type=BindingType.READ,
        name="span"
    )

    assert b.expression == "user.name"
    assert b.target_symbol == "sym1"
    assert b.binding_type == BindingType.READ
    assert b.name == "span"
    assert isinstance(b, TemplateNode)


def test_binding_empty_expression_allowed():
    b = Binding(
        expression="",
        target_symbol="sym1",
        binding_type=BindingType.READ
    )
    assert b.expression == ""


def test_binding_invalid_type():
    with pytest.raises(ValueError):
        BindingType("foo")


# ----------------------------
# DirectiveType
# ----------------------------

def test_directive_type_values():
    assert DirectiveType.LOOP.value == "loop"
    assert DirectiveType.CONDITIONAL.value == "if"
    assert DirectiveType.EVENT.value == "event"


def test_directive_type_invalid():
    with pytest.raises(ValueError):
        DirectiveType("repeat")


# ----------------------------
# Directive
# ----------------------------

def test_directive_creation():
    d = Directive(
        directive_type=DirectiveType.LOOP,
        expression="item in items",
        name="li"
    )

    assert d.directive_type == DirectiveType.LOOP
    assert d.expression == "item in items"
    assert d.name == "li"
    assert isinstance(d, TemplateNode)


# ----------------------------
# Template
# ----------------------------

def test_template_defaults():
    t = Template(name="root")
    assert t.bindings == []
    assert t.directives == []
    assert isinstance(t, TemplateNode)


def test_template_lists_isolated():
    t1 = Template()
    t2 = Template()

    t1.bindings.append(
        Binding(expression="x", target_symbol="s1", binding_type=BindingType.READ)
    )

    assert t2.bindings == []


def test_template_with_children():
    b = Binding(expression="x", target_symbol="s1", binding_type=BindingType.READ)
    d = Directive(directive_type=DirectiveType.EVENT, expression="onClick()")

    t = Template(bindings=[b], directives=[d])

    assert t.bindings == [b]
    assert t.directives == [d]


# ----------------------------
# Cross invariants
# ----------------------------

@pytest.mark.parametrize("obj", [
    TemplateNode(),
    Binding(expression="x", target_symbol="s", binding_type=BindingType.READ),
    Directive(directive_type=DirectiveType.EVENT, expression="x()"),
    Template()
])
def test_all_template_nodes_are_irnodes(obj):
    assert isinstance(obj, IRNode)
