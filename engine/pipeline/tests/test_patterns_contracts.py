from pipeline.patterns.base import PatternDetector
from pipeline.patterns.result import PatternResult
from pipeline.patterns.roles import SemanticRole
from pipeline.patterns.confidence import PatternConfidence


class DummyNode:
    def __init__(self, id):
        self.id = id


class DummyDetector(PatternDetector):
    def extract(self, analysis):
        return [
            (DummyNode("a"), SemanticRole.SERVICE, PatternConfidence(0.9, "x")),
            ("b", SemanticRole.CONTROLLER, PatternConfidence(0.8, "y")),
        ]


def test_pattern_detector_normalizes_list_output():
    d = DummyDetector()
    roles, conf = d.detect(analysis=None)

    assert roles["a"] == [SemanticRole.SERVICE]
    assert roles["b"] == [SemanticRole.CONTROLLER]
    assert conf["a"].value == 0.9
    assert conf["b"].value == 0.8


class DummyDetector2(PatternDetector):
    def extract(self, analysis):
        return PatternResult(
            roles_by_node={"x": [SemanticRole.SERVICE]},
            confidence_by_node={"x": PatternConfidence(0.7, "ok")},
        )


def test_pattern_detector_passthrough_pattern_result():
    d = DummyDetector2()
    roles, conf = d.detect(analysis=None)

    assert roles["x"] == [SemanticRole.SERVICE]
    assert conf["x"].value == 0.7
