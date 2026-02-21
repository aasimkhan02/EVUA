import pytest
from pipeline.transformation.base import TransformationStage
from pipeline.transformation.applier import RuleApplier
from pipeline.transformation.result import TransformationResult


def test_transformation_stage_is_abstract():
    with pytest.raises(TypeError):
        TransformationStage()


def test_transformation_result_defaults():
    r = TransformationResult()
    assert r.changes == []
    assert r.new_ir_nodes == []


def test_rule_applier_aggregates():
    class DummyRule:
        def apply(self, analysis, patterns):
            return ["a"]

    applier = RuleApplier([DummyRule(), DummyRule()])
    out = applier.apply_all(None, None)

    assert out == ["a", "a"]
