from __future__ import annotations

import json
import os
import resource
import shutil
import subprocess
import sys
import tempfile
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from .models import CaseResult, CaseStatus, EvaluationResult, RunStatus, TaskSpec

RESULT_MARKER = "__AGENT_EVAL_RESULT__="

HARNESS_SOURCE = r'''
import contextlib
import copy
import importlib.util
import io
import json
import time
import traceback

MARKER = "__AGENT_EVAL_RESULT__="


def safe_value(value):
    try:
        json.dumps(value)
        return value
    except (TypeError, ValueError):
        return repr(value)


def equivalent(actual, expected):
    if isinstance(expected, bool):
        return isinstance(actual, bool) and actual is expected
    return actual == expected


def main():
    config = json.loads(open("task.json", encoding="utf-8").read())
    cases = []
    try:
        spec = importlib.util.spec_from_file_location("candidate", "candidate.py")
        module = importlib.util.module_from_spec(spec)
        import_output = io.StringIO()
        with contextlib.redirect_stdout(import_output), contextlib.redirect_stderr(import_output):
            spec.loader.exec_module(module)
        function = getattr(module, config["function_name"])
    except BaseException as exc:
        payload = {
            "fatal_error": f"{type(exc).__name__}: {exc}",
            "import_output": import_output.getvalue() if "import_output" in locals() else "",
            "cases": [],
        }
        print(MARKER + json.dumps(payload, separators=(",", ":")))
        return

    for test in config["tests"]:
        started = time.perf_counter()
        output = io.StringIO()
        try:
            args = copy.deepcopy(test["args"])
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                actual = function(*args)
            passed = equivalent(actual, test["expected"])
            cases.append({
                "name": test["name"],
                "status": "passed" if passed else "failed",
                "duration_ms": round((time.perf_counter() - started) * 1000, 3),
                "expected": safe_value(test["expected"]),
                "actual": safe_value(actual),
                "error": None,
                "stdout": output.getvalue()[-2000:],
            })
        except BaseException as exc:
            cases.append({
                "name": test["name"],
                "status": "error",
                "duration_ms": round((time.perf_counter() - started) * 1000, 3),
                "expected": safe_value(test["expected"]),
                "actual": None,
                "error": f"{type(exc).__name__}: {exc}",
                "stdout": output.getvalue()[-2000:],
            })

    print(MARKER + json.dumps({"fatal_error": None, "cases": cases}, separators=(",", ":")))


if __name__ == "__main__":
    main()
'''


class SandboxRunner(ABC):
    name: str

    @abstractmethod
    def command(self, workspace: Path) -> list[str]:
        raise NotImplementedError

    def evaluate(self, task: TaskSpec, code: str, timeout_seconds: float = 4.0) -> EvaluationResult:
        started = time.perf_counter()
        workspace_root = os.getenv("RUNNER_WORKSPACE_ROOT")
        if workspace_root:
            Path(workspace_root).mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="agent-eval-", dir=workspace_root) as temporary:
            workspace = Path(temporary)
            (workspace / "candidate.py").write_text(code, encoding="utf-8")
            (workspace / "harness.py").write_text(HARNESS_SOURCE, encoding="utf-8")
            config = {
                "function_name": task.function_name,
                "tests": [item.model_dump(mode="json") for item in task.tests],
            }
            (workspace / "task.json").write_text(json.dumps(config), encoding="utf-8")
            workspace.chmod(0o755)

            try:
                completed = subprocess.run(
                    self.command(workspace),
                    cwd=workspace,
                    capture_output=True,
                    text=True,
                    timeout=timeout_seconds,
                    preexec_fn=self._limits
                    if self.name == "local" and sys.platform.startswith("linux")
                    else None,
                    env=self._environment(),
                )
            except subprocess.TimeoutExpired:
                return EvaluationResult(
                    status=RunStatus.TIMEOUT,
                    duration_ms=round((time.perf_counter() - started) * 1000, 2),
                    passed_cases=0,
                    total_cases=len(task.tests),
                    cases=[],
                    runner=self.name,
                    error=f"Execution exceeded {timeout_seconds:g} seconds.",
                )
            except (OSError, subprocess.SubprocessError) as exc:
                return self._runner_error(task, started, f"Runner could not start: {exc}")

        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        payload = self._extract_payload(completed.stdout)
        if payload is None:
            detail = completed.stderr.strip()[-1200:] or f"runner exited with code {completed.returncode}"
            return self._runner_error(task, started, detail, duration_ms)

        if payload.get("fatal_error"):
            return EvaluationResult(
                status=RunStatus.ERROR,
                duration_ms=duration_ms,
                passed_cases=0,
                total_cases=len(task.tests),
                cases=[],
                runner=self.name,
                error=str(payload["fatal_error"]),
            )

        cases = [CaseResult.model_validate(case) for case in payload.get("cases", [])]
        passed = sum(case.status == CaseStatus.PASSED for case in cases)
        has_error = any(case.status == CaseStatus.ERROR for case in cases)
        if passed == len(task.tests):
            status = RunStatus.PASSED
        elif has_error:
            status = RunStatus.ERROR
        else:
            status = RunStatus.FAILED
        return EvaluationResult(
            status=status,
            duration_ms=duration_ms,
            passed_cases=passed,
            total_cases=len(task.tests),
            cases=cases,
            runner=self.name,
            error=None,
        )

    @staticmethod
    def _environment() -> dict[str, str]:
        return {"PATH": os.environ.get("PATH", ""), "PYTHONHASHSEED": "0", "PYTHONIOENCODING": "utf-8"}

    @staticmethod
    def _limits() -> None:
        limits = (
            (resource.RLIMIT_CPU, (3, 3)),
            (resource.RLIMIT_AS, (256 * 1024 * 1024, 256 * 1024 * 1024)),
            (resource.RLIMIT_FSIZE, (1024 * 1024, 1024 * 1024)),
        )
        for kind, value in limits:
            try:
                resource.setrlimit(kind, value)
            except (OSError, ValueError):
                pass

    @staticmethod
    def _extract_payload(output: str) -> dict[str, Any] | None:
        for line in reversed(output.splitlines()):
            if line.startswith(RESULT_MARKER):
                try:
                    return json.loads(line[len(RESULT_MARKER) :])
                except json.JSONDecodeError:
                    return None
        return None

    def _runner_error(
        self,
        task: TaskSpec,
        started: float,
        error: str,
        duration_ms: float | None = None,
    ) -> EvaluationResult:
        return EvaluationResult(
            status=RunStatus.ERROR,
            duration_ms=duration_ms or round((time.perf_counter() - started) * 1000, 2),
            passed_cases=0,
            total_cases=len(task.tests),
            cases=[],
            runner=self.name,
            error=error,
        )


class LocalProcessRunner(SandboxRunner):
    name = "local"

    def command(self, workspace: Path) -> list[str]:
        return [sys.executable, "-I", str(workspace / "harness.py")]


class DockerRunner(SandboxRunner):
    name = "docker"

    def __init__(self, image: str = "agent-eval-runner:local") -> None:
        self.image = image

    def command(self, workspace: Path) -> list[str]:
        shared_volume = os.getenv("RUNNER_SHARED_VOLUME")
        if shared_volume:
            container_workspace = f"/runner-workspaces/{workspace.name}"
            workspace_mount = ["-v", f"{shared_volume}:/runner-workspaces:ro"]
        else:
            container_workspace = "/workspace"
            workspace_mount = ["-v", f"{workspace}:/workspace:ro"]
        return [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "--memory",
            "128m",
            "--cpus",
            "0.5",
            "--pids-limit",
            "64",
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,size=16m",
            "--user",
            "10001:10001",
            *workspace_mount,
            "-w",
            container_workspace,
            self.image,
            "python",
            "-I",
            f"{container_workspace}/harness.py",
        ]


def docker_is_ready(image: str) -> bool:
    if shutil.which("docker") is None:
        return False
    checks = (["docker", "info"], ["docker", "image", "inspect", image])
    for command in checks:
        try:
            result = subprocess.run(command, capture_output=True, timeout=2)
        except (OSError, subprocess.TimeoutExpired):
            return False
        if result.returncode != 0:
            return False
    return True


def create_runner(backend: str | None = None) -> SandboxRunner:
    selected = (backend or os.getenv("RUNNER_BACKEND", "auto")).lower()
    image = os.getenv("RUNNER_IMAGE", "agent-eval-runner:local")
    if selected == "docker":
        return DockerRunner(image)
    if selected == "local":
        return LocalProcessRunner()
    if selected == "auto":
        return DockerRunner(image) if docker_is_ready(image) else LocalProcessRunner()
    raise ValueError(f"Unknown runner backend: {selected}")
