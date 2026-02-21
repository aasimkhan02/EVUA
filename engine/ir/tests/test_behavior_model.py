import pytest

from ir.behavior_model.base import Behavior
from ir.behavior_model.binding import RuntimeBinding, BindingSemantics
from ir.behavior_model.lifecycle import LifecycleHook, LifecyclePhase
from ir.behavior_model.observer import Observer
from ir.behavior_model.side_effect import SideEffect


# ---------------------------
# Base Behavior
# ---------------------------

def test_behavior_base_fields():
    b = Behavior(description="test behavior")
    assert b.description == "test behavior"


def test_behavior_is_irnode():
    b = Behavior(description="x")
    from ir.code_model.base import IRNode
    assert isinstance(b, IRNode)


# ---------------------------
# RuntimeBinding
# ---------------------------

def test_runtime_binding_creation():
    rb = RuntimeBinding(
        description="ng-model binding",
        source_symbol_id="sym1",
        target_symbol_id="sym2",
        semantics=BindingSemantics.TWO_WAY,
    )

    assert rb.source_symbol_id == "sym1"
    assert rb.target_symbol_id == "sym2"
    assert rb.semantics == BindingSemantics.TWO_WAY
    assert rb.description == "ng-model binding"


def test_runtime_binding_enum_values():
    assert BindingSemantics.ONE_WAY.value == "one_way"
    assert BindingSemantics.TWO_WAY.value == "two_way"
    assert BindingSemantics.IMPLICIT.value == "implicit"


def test_runtime_binding_invalid_enum():
    with pytest.raises(ValueError):
        BindingSemantics("three_way")


def test_runtime_binding_empty_ids_allowed():
    rb = RuntimeBinding(
        description="",
        source_symbol_id="",
        target_symbol_id="",
        semantics=BindingSemantics.IMPLICIT,
    )
    assert rb.source_symbol_id == ""
    assert rb.target_symbol_id == ""


# ---------------------------
# LifecycleHook
# ---------------------------

def test_lifecycle_hook_creation():
    hook = LifecycleHook(
        description="on init",
        phase=LifecyclePhase.INIT,
        owner_id="component_1"
    )

    assert hook.phase == LifecyclePhase.INIT
    assert hook.owner_id == "component_1"
    assert hook.description == "on init"


def test_lifecycle_phase_enum_values():
    assert LifecyclePhase.INIT.value == "init"
    assert LifecyclePhase.UPDATE.value == "update"
    assert LifecyclePhase.DESTROY.value == "destroy"


def test_lifecycle_invalid_phase():
    with pytest.raises(ValueError):
        LifecyclePhase("mount")


# ---------------------------
# Observer
# ---------------------------

def test_observer_creation():
    obs = Observer(
        description="deep watch on obj",
        observed_symbol_id="symX",
        trigger="deep_change"
    )

    assert obs.observed_symbol_id == "symX"
    assert obs.trigger == "deep_change"
    assert obs.description == "deep watch on obj"


def test_observer_invalid_trigger_type():
    obs = Observer(
        description="bad trigger",
        observed_symbol_id="sym1",
        trigger=123   # no validation yet, should be accepted but flagged later
    )
    assert obs.trigger == 123


# ---------------------------
# SideEffect
# ---------------------------

def test_side_effect_creation():
    se = SideEffect(
        description="mutation in digest",
        cause="watcher",
        affected_symbol_id="symY"
    )

    assert se.cause == "watcher"
    assert se.affected_symbol_id == "symY"
    assert se.description == "mutation in digest"


def test_side_effect_empty_fields():
    se = SideEffect(
        description="",
        cause="",
        affected_symbol_id=""
    )
    assert se.cause == ""
    assert se.affected_symbol_id == ""


# ---------------------------
# Cross-type invariants
# ---------------------------

@pytest.mark.parametrize("cls, kwargs", [
    (RuntimeBinding, dict(description="d", source_symbol_id="a", target_symbol_id="b", semantics=BindingSemantics.ONE_WAY)),
    (LifecycleHook, dict(description="d", phase=LifecyclePhase.UPDATE, owner_id="c1")),
    (Observer, dict(description="d", observed_symbol_id="s1", trigger="change")),
    (SideEffect, dict(description="d", cause="event", affected_symbol_id="s2")),
])
def test_all_behaviors_are_irnodes(cls, kwargs):
    obj = cls(**kwargs)
    from ir.code_model.base import IRNode
    assert isinstance(obj, IRNode)


# ---------------------------
# Optional: Serialization (if IRNode supports it)
# ---------------------------

def test_behavior_serialization_if_supported():
    b = Behavior(description="serialize me")

    if hasattr(b, "to_dict"):
        d = b.to_dict()
        assert d["description"] == "serialize me"
        assert "id" in d
        assert "type" in d
