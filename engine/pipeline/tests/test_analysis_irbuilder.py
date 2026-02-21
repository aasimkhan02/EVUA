from pipeline.analysis.builder import IRBuilder
from ir.dependency_model.edge import DependencyEdge
from ir.dependency_model.base import DependencyType, DependencyMetadata


class FakeRawModule:
    def __init__(self):
        self.name = "Ctrl"
        self.file = "a.js"
        self.scope_reads = ["x"]
        self.scope_writes = ["y"]
        self.watch_depths = ["deep"]
        self.uses_compile = True
        self.has_nested_scopes = True


class FakeRawDirective:
    def __init__(self, name="d", has_compile=True, has_link=False, transclude=True):
        self.name = name
        self.has_compile = has_compile
        self.has_link = has_link
        self.transclude = transclude


class FakeRawTemplate:
    def __init__(self):
        self.bindings = []
        self.directives = []


class FakeEdge:
    def __init__(self):
        self.source_id = "a"
        self.target_id = "b"
        self.type = DependencyType.IMPORT
        self.metadata = DependencyMetadata()


def test_irbuilder_build_happy_path():
    b = IRBuilder()
    raw_modules = [FakeRawModule()]
    raw_templates = [FakeRawTemplate()]
    raw_edges = [FakeEdge()]
    raw_directives = [FakeRawDirective()]
    raw_http = ["http1"]

    modules, deps, templates, behaviors = b.build(
        (raw_modules, raw_templates, raw_edges, raw_directives, raw_http)
    )

    assert len(modules) == 1
    assert modules[0].classes[0].scope_reads == ["x"]
    assert deps.depends_on("a", "b") is True
    assert len(templates) == 1
    assert len(behaviors) == 2  # compile + transclude side-effects


def test_irbuilder_empty_inputs():
    b = IRBuilder()
    modules, deps, templates, behaviors = b.build(([], [], [], [], []))
    assert modules == []
    assert deps.edges == []
    assert templates == []
    assert behaviors == []
