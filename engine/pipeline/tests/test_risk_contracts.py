import pytest
from pipeline.risk.base import RiskStage
from pipeline.risk.levels import RiskLevel
from pipeline.risk.result import RiskResult


def test_risk_stage_is_abstract():
    with pytest.raises(TypeError):
        RiskStage()


def test_risk_level_values():
    assert RiskLevel.SAFE.value == "safe"
    assert RiskLevel.RISKY.value == "risky"
    assert RiskLevel.MANUAL.value == "manual"


def test_risk_result_basic():
    r = RiskResult(risk_by_change_id={"1": RiskLevel.SAFE}, reason_by_change_id={"1": "ok"})
    assert r.risk_by_change_id["1"] == RiskLevel.SAFE
    assert r.reason_by_change_id["1"] == "ok"
