import json
from pathlib import Path

import pytest

from orchestration.pipeline_runner import PipelineRunner


# ---------------------------
# Helpers
# ---------------------------

def write_file(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# ---------------------------
# Tests
# ---------------------------

def test_orchestration_happy_path_no_rollback(tmp_path, monkeypatch):
    """
    Pipeline passes -> no rollback, backup cleared, progress saved.
    """
    out_root = tmp_path / "out"

    # Pre-existing file
    f1 = out_root / "a.txt"
    write_file(f1, "hello")

    called = {"ran": False}

    def fake_pipeline_fn():
        # Modify file + create new file
        write_file(f1, "hello world")  # updated
        write_file(out_root / "b.txt", "new")  # created
        called["ran"] = True
        return True  # validation_passed

    runner = PipelineRunner(pipeline_fn=fake_pipeline_fn, out_root=str(out_root))
    passed = runner.run()

    assert passed is True
    assert called["ran"] is True

    # Progress log exists
    progress_path = out_root / "progress.json"
    assert progress_path.exists()

    entries = json.loads(progress_path.read_text(encoding="utf-8"))
    actions = {e["action"] for e in entries}

    assert "updated" in actions
    assert "created" in actions

    # Backup directory should be cleared on success
    assert not (out_root / ".backup").exists()


def test_orchestration_failure_triggers_rollback(tmp_path):
    """
    Pipeline fails -> rollback restores original files.
    """
    out_root = tmp_path / "out"

    f1 = out_root / "a.txt"
    write_file(f1, "ORIGINAL")

    def fake_pipeline_fn():
        # Break stuff
        write_file(f1, "BROKEN")
        write_file(out_root / "b.txt", "new")
        return False  # validation failed

    runner = PipelineRunner(pipeline_fn=fake_pipeline_fn, out_root=str(out_root))
    passed = runner.run()

    assert passed is False

    # File restored
    assert f1.read_text(encoding="utf-8") == "ORIGINAL"

    # Progress records rollback
    progress_path = out_root / "progress.json"
    entries = json.loads(progress_path.read_text(encoding="utf-8"))
    actions = [e["action"] for e in entries]

    assert "rolled_back" in actions


def test_orchestration_idempotency_records_unchanged(tmp_path):
    """
    No changes -> files should be marked unchanged.
    """
    out_root = tmp_path / "out"

    f1 = out_root / "a.txt"
    write_file(f1, "SAME")

    def fake_pipeline_fn():
        # Does nothing
        return True

    runner = PipelineRunner(pipeline_fn=fake_pipeline_fn, out_root=str(out_root))
    passed = runner.run()

    assert passed is True

    entries = json.loads((out_root / "progress.json").read_text(encoding="utf-8"))
    actions = {e["action"] for e in entries}

    assert "unchanged" in actions


def test_orchestration_removed_files_detected(tmp_path):
    """
    File removed during pipeline -> recorded as removed.
    """
    out_root = tmp_path / "out"

    f1 = out_root / "a.txt"
    write_file(f1, "bye")

    def fake_pipeline_fn():
        f1.unlink()  # remove file
        return True

    runner = PipelineRunner(pipeline_fn=fake_pipeline_fn, out_root=str(out_root))
    passed = runner.run()

    assert passed is True

    entries = json.loads((out_root / "progress.json").read_text(encoding="utf-8"))
    actions = [e["action"] for e in entries]

    assert "removed" in actions


def test_orchestration_exception_triggers_rollback(tmp_path):
    """
    Pipeline crashes -> rollback should occur.
    """
    out_root = tmp_path / "out"

    f1 = out_root / "a.txt"
    write_file(f1, "SAFE")

    def crashing_pipeline_fn():
        write_file(f1, "BROKEN")
        raise RuntimeError("boom")

    runner = PipelineRunner(pipeline_fn=crashing_pipeline_fn, out_root=str(out_root))
    passed = runner.run()

    assert passed is False
    assert f1.read_text(encoding="utf-8") == "SAFE"

    entries = json.loads((out_root / "progress.json").read_text(encoding="utf-8"))
    actions = [e["action"] for e in entries]
    assert "rolled_back" in actions
