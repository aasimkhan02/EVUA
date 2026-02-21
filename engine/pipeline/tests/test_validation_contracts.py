import pytest
from pipeline.validation.base import ValidationStage
from pipeline.validation.result import ValidationResult


def test_validation_stage_is_abstract():
    with pytest.raises(TypeError):
        ValidationStage()


def test_validation_result_fields():
    r = ValidationResult(passed=True, checks={"lint": True}, failures=[])
    assert r.passed is True
    assert r.checks["lint"] is True
    assert r.failures == []
