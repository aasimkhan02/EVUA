from types import SimpleNamespace
from pipeline.analysis.dispatcher import AnalyzerDispatcher
from pipeline.ingestion.classifier import FileType


class FakeRawModule:
    def __init__(self, name, file):
        self.name = name
        self.file = file
        self.scope_reads = []
        self.scope_writes = []
        self.watch_depths = []
        self.uses_compile = False
        self.has_nested_scopes = False


class DummyAnalyzer:
    def __init__(self, tag):
        self.tag = tag

    def analyze(self, paths):
        # Return a valid "raw module" shape so dispatcher doesn't filter it out
        return (
            [FakeRawModule(name=f"{self.tag}Ctrl", file=f"{self.tag}.js")],
            [],  # raw_templates
            [],  # raw_edges
            [],  # raw_directives
            [],  # raw_http_calls
        )


def test_dispatcher_aggregates(monkeypatch):
    d = AnalyzerDispatcher()

    monkeypatch.setattr(d, "get_analyzer", lambda ft: DummyAnalyzer(ft.value))

    result = d.dispatch({
        FileType.JS: ["a.js"],
        FileType.HTML: ["a.html"],
    })

    assert len(result.modules) == 2
    assert len(result.templates) == 0
