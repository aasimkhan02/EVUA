import pytest
from pipeline.patterns.roles import SemanticRole
from pipeline.patterns.confidence import PatternConfidence
from pipeline.patterns.knowledge_base import PatternKnowledgeBase, PatternMapping


def test_semantic_role_enum_values():
    assert SemanticRole.CONTROLLER.value == "controller"
    assert SemanticRole.SERVICE.value == "service"
    assert SemanticRole.HTTP_CALL.value == "http_call"


def test_semantic_role_invalid():
    with pytest.raises(ValueError):
        SemanticRole("random")


def test_pattern_confidence_basic():
    c = PatternConfidence(0.5, "meh")
    assert c.value == 0.5
    assert c.explanation == "meh"


def test_pattern_kb_register_and_get():
    kb = PatternKnowledgeBase()
    m = PatternMapping(
        pattern_name="ctrl",
        role=SemanticRole.CONTROLLER,
        confidence_hint=0.9,
        description="controller pattern",
    )
    kb.register(m)
    assert kb.get("ctrl") == m
    assert kb.get("missing") is None
