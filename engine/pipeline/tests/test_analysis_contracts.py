import pytest
from pipeline.analysis.base import AnalysisStage
from pipeline.analysis.analyzers.base import Analyzer
from pipeline.analysis.dispatcher import AnalyzerDispatcher
from pipeline.analysis.result import AnalysisResult
from pipeline.ingestion.classifier import FileType


def test_analysis_stage_is_abstract():
    with pytest.raises(TypeError):
        AnalysisStage()


def test_analyzer_is_abstract():
    with pytest.raises(TypeError):
        Analyzer()


def test_dispatcher_get_analyzer_known():
    d = AnalyzerDispatcher()
    assert d.get_analyzer(FileType.JS) is not None
    assert d.get_analyzer(FileType.HTML) is not None
    assert d.get_analyzer(FileType.PY) is not None
    assert d.get_analyzer(FileType.JAVA) is not None


def test_dispatcher_get_analyzer_unknown():
    d = AnalyzerDispatcher()
    assert d.get_analyzer(FileType.OTHER) is None


def test_analysis_result_fields():
    r = AnalysisResult(modules=[], dependencies=None, templates=[], behaviors=[], http_calls=[])
    assert r.modules == []
    assert r.templates == []
    assert r.behaviors == []
    assert r.http_calls == []
