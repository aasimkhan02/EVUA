import subprocess
from pathlib import Path

from pipeline.validation.runners.lint import LintRunner
from pipeline.validation.runners.tests import TestRunner


def test_lint_runner_stub():
    assert LintRunner().run("any") is True


def test_test_runner_angular_out(monkeypatch, tmp_path):
    angular_out = tmp_path / "out" / "angular-app"
    (angular_out / "angular.json").mkdir(parents=True, exist_ok=True)

    def fake_run(cmd, cwd, capture_output, text, timeout):
        class R:
            returncode = 0
            stdout = "ok"
            stderr = ""
        return R()

    monkeypatch.setattr(subprocess, "run", fake_run)

    runner = TestRunner()
    passed, output = runner.run(str(tmp_path))

    assert passed is True
    assert "ok" in output


def test_test_runner_fallback_npm(monkeypatch, tmp_path):
    def fake_run(cmd, cwd, capture_output, text, timeout):
        class R:
            returncode = 1
            stdout = ""
            stderr = "fail"
        return R()

    monkeypatch.setattr(subprocess, "run", fake_run)

    runner = TestRunner()
    passed, output = runner.run(str(tmp_path))

    assert passed is False
    assert "fail" in output


def test_test_runner_command_not_found(monkeypatch, tmp_path):
    def fake_run(*args, **kwargs):
        raise FileNotFoundError("ng")

    monkeypatch.setattr(subprocess, "run", fake_run)

    runner = TestRunner()
    passed, output = runner.run(str(tmp_path))

    assert passed is False
    assert "Test command not found" in output
