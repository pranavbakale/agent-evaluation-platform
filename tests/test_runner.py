from __future__ import annotations

import os

import pytest

from agent_eval.catalog import get_task
from agent_eval.models import RunStatus
from agent_eval.runner import DockerRunner, LocalProcessRunner, create_runner


def test_valid_solution_passes_every_case() -> None:
    task = get_task("sum-numbers")
    assert task is not None
    result = LocalProcessRunner().evaluate(task, task.reference_code)
    assert result.status == RunStatus.PASSED
    assert result.passed_cases == result.total_cases == 4
    assert all(case.status.value == "passed" for case in result.cases)


def test_wrong_solution_produces_inspectable_failures() -> None:
    task = get_task("clamp-value")
    assert task is not None
    result = LocalProcessRunner().evaluate(task, "def clamp(value, lower, upper):\n    return value\n")
    assert result.status == RunStatus.FAILED
    assert result.passed_cases < result.total_cases
    assert any(case.actual != case.expected for case in result.cases)


def test_syntax_error_is_reported_without_a_traceback_leak() -> None:
    task = get_task("factorial")
    assert task is not None
    result = LocalProcessRunner().evaluate(task, "def factorial(n)\n    return 1\n")
    assert result.status == RunStatus.ERROR
    assert result.error is not None
    assert "SyntaxError" in result.error
    assert "Traceback" not in result.error


def test_timeout_stops_non_terminating_submission() -> None:
    task = get_task("factorial")
    assert task is not None
    result = LocalProcessRunner().evaluate(task, "def factorial(n):\n    while True:\n        pass\n", timeout_seconds=0.2)
    assert result.status == RunStatus.TIMEOUT


def test_runner_factory_rejects_unknown_backend() -> None:
    with pytest.raises(ValueError, match="Unknown runner backend"):
        create_runner("not-real")


def test_docker_runner_uses_named_volume_for_compose(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("RUNNER_SHARED_VOLUME", "evaluation-workspaces")
    command = DockerRunner().command(tmp_path / "agent-eval-example")
    assert "evaluation-workspaces:/runner-workspaces:ro" in command
    assert "/runner-workspaces/agent-eval-example/harness.py" in command


@pytest.mark.docker
@pytest.mark.skipif(os.getenv("RUNNER_BACKEND") != "docker", reason="Docker runner not requested")
def test_docker_runner_executes_in_restricted_container() -> None:
    task = get_task("normalize-whitespace")
    assert task is not None
    result = DockerRunner().evaluate(task, task.reference_code, timeout_seconds=10)
    assert result.status == RunStatus.PASSED
    assert result.runner == "docker"
