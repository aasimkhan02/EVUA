import pytest
from pathlib import Path

from pipeline.ingestion.base import IngestionStage
from pipeline.ingestion.classifier import FileClassifier, FileType
from pipeline.ingestion.scanner import FileScanner
from pipeline.ingestion.result import IngestionResult
from pipeline.ingestion.source import Source


# ----------------------------
# FileClassifier
# ----------------------------

def test_file_classifier_known_types(tmp_path):
    c = FileClassifier()

    assert c.classify(tmp_path / "a.js") == FileType.JS
    assert c.classify(tmp_path / "b.ts") == FileType.TS
    assert c.classify(tmp_path / "c.html") == FileType.HTML
    assert c.classify(tmp_path / "d.py") == FileType.PY
    assert c.classify(tmp_path / "e.java") == FileType.JAVA


def test_file_classifier_case_insensitive(tmp_path):
    c = FileClassifier()
    assert c.classify(tmp_path / "A.JS") == FileType.JS


def test_file_classifier_unknown(tmp_path):
    c = FileClassifier()
    assert c.classify(tmp_path / "readme.md") == FileType.OTHER


# ----------------------------
# FileScanner
# ----------------------------

def test_file_scanner_basic(tmp_path):
    # Create structure
    (tmp_path / "a.js").write_text("x")
    (tmp_path / "b.py").write_text("y")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "c.html").write_text("z")

    s = FileScanner()
    files = s.scan(str(tmp_path))

    paths = {p.name for p in files}
    assert paths == {"a.js", "b.py", "c.html"}


def test_file_scanner_ignores_dirs(tmp_path):
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "x.js").write_text("bad")

    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "y.js").write_text("bad")

    (tmp_path / "ok.js").write_text("good")

    s = FileScanner()
    files = s.scan(str(tmp_path))

    names = [p.name for p in files]
    assert "ok.js" in names
    assert "x.js" not in names
    assert "y.js" not in names


def test_file_scanner_empty_dir(tmp_path):
    s = FileScanner()
    files = s.scan(str(tmp_path))
    assert files == []


def test_file_scanner_nonexistent_path():
    s = FileScanner()
    with pytest.raises(Exception):
        s.scan("/this/path/does/not/exist")


# ----------------------------
# IngestionResult
# ----------------------------

def test_ingestion_result_defaults():
    r = IngestionResult()
    assert r.files_by_type == {}
    assert r.root_path == ""


def test_ingestion_result_isolated():
    r1 = IngestionResult()
    r2 = IngestionResult()

    r1.files_by_type[FileType.JS] = [Path("a.js")]
    assert r2.files_by_type == {}


# ----------------------------
# IngestionStage (ABC)
# ----------------------------

def test_ingestion_stage_is_abstract():
    with pytest.raises(TypeError):
        IngestionStage()


def test_ingestion_stage_contract():
    class DummyStage(IngestionStage):
        def ingest(self):
            return IngestionResult(root_path="x")

    d = DummyStage()
    res = d.ingest()
    assert isinstance(res, IngestionResult)


# ----------------------------
# Source
# ----------------------------

def test_source_basic():
    s = Source(root_path="/repo")
    assert s.root_path == "/repo"
