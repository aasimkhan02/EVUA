from types import SimpleNamespace

from pipeline.risk.rules.service_risk import ServiceRiskRule
from pipeline.risk.rules.angularjs.template_binding_risk import TemplateBindingRiskRule
from pipeline.risk.rules.angularjs.watcher_risk import WatcherRiskRule
from pipeline.risk.levels import RiskLevel
from pipeline.patterns.roles import SemanticRole


class FakeChange:
    def __init__(self, id, before_id, reason):
        self.id = id
        self.before_id = before_id
        self.reason = reason


class FakeClass:
    def __init__(self, id, scope_writes=None, watch_depths=None, uses_compile=False, has_nested_scopes=False):
        self.id = id
        self.scope_writes = scope_writes or []
        self.watch_depths = watch_depths or []
        self.uses_compile = uses_compile
        self.has_nested_scopes = has_nested_scopes


def test_service_risk_rule_safe_cases():
    changes = [
        FakeChange("1", "a", "Service Foo"),
        FakeChange("2", "b", "$http -> HttpClient"),
    ]
    transformation = SimpleNamespace(changes=changes)

    risk, reason = ServiceRiskRule().assess(None, None, transformation)

    assert risk["1"] == RiskLevel.SAFE
    assert risk["2"] == RiskLevel.SAFE


def test_template_binding_risk_manual():
    change = FakeChange("1", "node1", "Template migration")
    patterns = SimpleNamespace(roles_by_node={
        "node1": [SemanticRole.TEMPLATE_BINDING, SemanticRole.EVENT_HANDLER]
    })
    transformation = SimpleNamespace(changes=[change])

    risk, _ = TemplateBindingRiskRule().assess(None, patterns, transformation)
    assert risk["1"] == RiskLevel.MANUAL


def test_template_binding_risk_risky():
    change = FakeChange("1", "node1", "Template migration")
    patterns = SimpleNamespace(roles_by_node={
        "node1": [SemanticRole.TEMPLATE_BINDING]
    })
    transformation = SimpleNamespace(changes=[change])

    risk, _ = TemplateBindingRiskRule().assess(None, patterns, transformation)
    assert risk["1"] == RiskLevel.RISKY


def test_template_binding_risk_safe():
    change = FakeChange("1", "node1", "Template migration")
    patterns = SimpleNamespace(roles_by_node={})
    transformation = SimpleNamespace(changes=[change])

    risk, _ = TemplateBindingRiskRule().assess(None, patterns, transformation)
    assert risk["1"] == RiskLevel.SAFE


def test_watcher_risk_deep_manual():
    c = FakeClass("A", watch_depths=["deep"])
    analysis = SimpleNamespace(modules=[SimpleNamespace(classes=[c])])
    change = FakeChange("1", "A", "watch migration")
    transformation = SimpleNamespace(changes=[change])

    risk, _ = WatcherRiskRule().assess(analysis, None, transformation)
    assert risk["1"] == RiskLevel.MANUAL


def test_watcher_risk_shallow_heavy_writes_risky():
    c = FakeClass("A", watch_depths=["shallow"], scope_writes=["a", "b", "c"])
    analysis = SimpleNamespace(modules=[SimpleNamespace(classes=[c])])
    change = FakeChange("1", "A", "watch migration")
    transformation = SimpleNamespace(changes=[change])

    risk, _ = WatcherRiskRule().assess(analysis, None, transformation)
    assert risk["1"] == RiskLevel.RISKY


def test_watcher_risk_shallow_light_writes_safe():
    c = FakeClass("A", watch_depths=["shallow"], scope_writes=["a"])
    analysis = SimpleNamespace(modules=[SimpleNamespace(classes=[c])])
    change = FakeChange("1", "A", "watch migration")
    transformation = SimpleNamespace(changes=[change])

    risk, _ = WatcherRiskRule().assess(analysis, None, transformation)
    assert risk["1"] == RiskLevel.SAFE


def test_watcher_risk_nested_scopes_manual():
    c = FakeClass("A", has_nested_scopes=True)
    analysis = SimpleNamespace(modules=[SimpleNamespace(classes=[c])])
    change = FakeChange("1", "A", "watch migration")
    transformation = SimpleNamespace(changes=[change])

    risk, _ = WatcherRiskRule().assess(analysis, None, transformation)
    assert risk["1"] == RiskLevel.MANUAL


def test_watcher_risk_no_match_defaults_safe():
    analysis = SimpleNamespace(modules=[])
    change = FakeChange("1", "A", "watch migration")
    transformation = SimpleNamespace(changes=[change])

    risk, _ = WatcherRiskRule().assess(analysis, None, transformation)
    assert risk["1"] == RiskLevel.SAFE
