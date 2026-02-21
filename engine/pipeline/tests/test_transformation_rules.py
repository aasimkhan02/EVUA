from types import SimpleNamespace
from pathlib import Path

from pipeline.transformation.rules.angularjs.controller_to_component import ControllerToComponentRule
from pipeline.transformation.rules.angularjs.http_to_httpclient import HttpToHttpClientRule
from pipeline.transformation.rules.angularjs.service_to_injectable import ServiceToInjectableRule
from pipeline.transformation.rules.angularjs.simple_watch_to_rxjs import SimpleWatchToRxjsRule
from pipeline.patterns.roles import SemanticRole


class FakeClass:
    def __init__(self, id, name):
        self.id = id
        self.name = name


def test_controller_to_component_creates_files(tmp_path):
    c = FakeClass("1", "UserController")
    analysis = SimpleNamespace(modules=[SimpleNamespace(classes=[c])])
    patterns = SimpleNamespace(roles_by_node={})

    rule = ControllerToComponentRule(out_dir=tmp_path)
    changes = rule.apply(analysis, patterns)

    assert changes
    assert (tmp_path / "src" / "app" / "user.component.ts").exists()
    assert (tmp_path / "src" / "app" / "app-routing.module.ts").exists()


def test_service_to_injectable(tmp_path):
    patterns = SimpleNamespace(roles_by_node={"x": [SemanticRole.SERVICE]})
    analysis = None

    rule = ServiceToInjectableRule(out_dir=tmp_path)
    changes = rule.apply(analysis, patterns)

    assert changes
    service_file = list((tmp_path / "src" / "app").glob("*.service.ts"))
    assert service_file


def test_simple_watch_to_rxjs(tmp_path):
    node = SimpleNamespace(id="1", name="UserController")
    patterns = SimpleNamespace(matched_patterns=[(node, SemanticRole.SHALLOW_WATCH, None)])
    analysis = None

    rule = SimpleWatchToRxjsRule(out_dir=tmp_path)
    changes = rule.apply(analysis, patterns)

    assert changes
    component_ts = tmp_path / "src" / "app" / "user.component.ts"
    text = component_ts.read_text(encoding="utf-8")
    assert "BehaviorSubject" in text


def test_http_to_httpclient_noop_when_no_http_calls(tmp_path):
    patterns = SimpleNamespace(matched_patterns=[])
    analysis = None

    rule = HttpToHttpClientRule(out_dir=tmp_path)
    changes = rule.apply(analysis, patterns)

    assert changes == []
