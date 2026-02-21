from types import SimpleNamespace

from pipeline.patterns.detectors.angularjs.controller_detector import ControllerDetector
from pipeline.patterns.detectors.angularjs.http_detector import HttpDetector
from pipeline.patterns.detectors.angularjs.service_detector import ServiceDetector
from pipeline.patterns.detectors.angularjs.simple_watch_detector import SimpleWatchDetector
from pipeline.patterns.detectors.angularjs.template_binding_detector import TemplateBindingDetector
from pipeline.patterns.roles import SemanticRole


class FakeClass:
    def __init__(self, id, name, uses_compile=False, has_nested_scopes=False, watch_depths=None):
        self.id = id
        self.name = name
        self.uses_compile = uses_compile
        self.has_nested_scopes = has_nested_scopes
        self.watch_depths = watch_depths or []


class FakeDirective:
    def __init__(self, id, directive_type=None, has_compile=False, has_link=False, transclude=False):
        self.id = id
        self.directive_type = directive_type
        self.has_compile = has_compile
        self.has_link = has_link
        self.transclude = transclude


def test_controller_detector_roles():
    c = FakeClass("1", "UserController", uses_compile=True, has_nested_scopes=True, watch_depths=["deep"])
    analysis = SimpleNamespace(modules=[SimpleNamespace(classes=[c])])

    roles, conf = ControllerDetector().detect(analysis)

    assert SemanticRole.CONTROLLER in roles["1"]
    assert SemanticRole.COMPONENT_METHOD in roles["1"]
    assert SemanticRole.COMPONENT_STATE in roles["1"]
    assert SemanticRole.TEMPLATE_BINDING in roles["1"]


def test_http_detector():
    call = SimpleNamespace(id="h1")
    analysis = SimpleNamespace(http_calls=[call])

    roles, conf = HttpDetector().detect(analysis)

    assert roles[call.id] == [SemanticRole.HTTP_CALL]


def test_service_detector():
    c = FakeClass("2", "UserService")
    analysis = SimpleNamespace(modules=[SimpleNamespace(classes=[c])])

    roles, conf = ServiceDetector().detect(analysis)

    assert roles["2"] == [SemanticRole.SERVICE]


def test_simple_watch_detector_shallow_only():
    c = FakeClass("3", "Ctrl", watch_depths=["shallow"])
    analysis = SimpleNamespace(modules=[SimpleNamespace(classes=[c])])

    roles, conf = SimpleWatchDetector().detect(analysis)

    assert roles["3"] == [SemanticRole.SHALLOW_WATCH]


def test_simple_watch_detector_ignores_deep():
    c = FakeClass("4", "Ctrl", watch_depths=["deep"])
    analysis = SimpleNamespace(modules=[SimpleNamespace(classes=[c])])

    roles, conf = SimpleWatchDetector().detect(analysis)

    assert "4" not in roles


def test_template_binding_detector_template_directives():
    d = FakeDirective("5", directive_type="if")
    t = SimpleNamespace(directives=[d])
    analysis = SimpleNamespace(templates=[t], directives=[])

    roles, conf = TemplateBindingDetector().detect(analysis)

    assert SemanticRole.EVENT_HANDLER in roles["5"]
    assert SemanticRole.TEMPLATE_BINDING in roles["5"]


def test_template_binding_detector_js_directives():
    d = FakeDirective("6", has_compile=True, transclude=True)
    analysis = SimpleNamespace(templates=[], directives=[d])

    roles, conf = TemplateBindingDetector().detect(analysis)

    assert SemanticRole.TEMPLATE_BINDING in roles["6"]
