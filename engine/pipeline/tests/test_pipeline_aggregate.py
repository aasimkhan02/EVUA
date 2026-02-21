import json
from pathlib import Path

import pytest

from orchestration.pipeline_runner import PipelineRunner


def write_file(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_pipeline_runner_happy_path(tmp_path):
    """
    pipeline_fn returns True -> no rollback, backup cleared, progress saved.
    """
    out_root = tmp_path / "out"

    f1 = out_root / "a.txt"
    write_file(f1, "hello")

    def fake_pipeline_fn():
        write_file(f1, "hello world")          # updated
        write_file(out_root / "b.txt", "new")  # created
        return True

    runner = PipelineRunner(pipeline_fn=fake_pipeline_fn, out_root=str(out_root))
    passed = runner.run()

    assert passed is True

    # progress.json created
    progress_path = out_root / "progress.json"
    assert progress_path.exists()

    entries = json.loads(progress_path.read_text(encoding="utf-8"))
    actions = {e["action"] for e in entries}

    assert "updated" in actions
    assert "created" in actions

    # backup cleared on success
    assert not (out_root / ".backup").exists()


def test_pipeline_runner_failure_triggers_rollback(tmp_path):
    """
    pipeline_fn returns False -> rollback restores original files.
    """
    out_root = tmp_path / "out"

    f1 = out_root / "a.txt"
    write_file(f1, "ORIGINAL")

    def fake_pipeline_fn():
        write_file(f1, "BROKEN")
        write_file(out_root / "b.txt", "new")
        return False

    runner = PipelineRunner(pipeline_fn=fake_pipeline_fn, out_root=str(out_root))
    passed = runner.run()

    assert passed is False
    assert f1.read_text(encoding="utf-8") == "ORIGINAL"

    entries = json.loads((out_root / "progress.json").read_text(encoding="utf-8"))
    actions = [e["action"] for e in entries]
    assert "rolled_back" in actions


def test_pipeline_runner_exception_triggers_rollback(tmp_path):
    """
    pipeline_fn raises -> rollback should restore files.
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


def test_pipeline_runner_idempotency_records_unchanged(tmp_path):
    """
    No changes -> files marked unchanged.
    """
    out_root = tmp_path / "out"

    f1 = out_root / "a.txt"
    write_file(f1, "SAME")

    def fake_pipeline_fn():
        return True

    runner = PipelineRunner(pipeline_fn=fake_pipeline_fn, out_root=str(out_root))
    passed = runner.run()

    assert passed is True

    entries = json.loads((out_root / "progress.json").read_text(encoding="utf-8"))
    actions = {e["action"] for e in entries}

    assert "unchanged" in actions


def test_pipeline_runner_removed_files_detected(tmp_path):
    """
    Removed files should be recorded.
    """
    out_root = tmp_path / "out"

    f1 = out_root / "a.txt"
    write_file(f1, "bye")

    def fake_pipeline_fn():
        f1.unlink()
        return True

    runner = PipelineRunner(pipeline_fn=fake_pipeline_fn, out_root=str(out_root))
    passed = runner.run()

    assert passed is True

    entries = json.loads((out_root / "progress.json").read_text(encoding="utf-8"))
    actions = [e["action"] for e in entries]

    assert "removed" in actions
