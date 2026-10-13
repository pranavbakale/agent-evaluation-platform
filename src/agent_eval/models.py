from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TestVector(BaseModel):
    name: str
    args: list[Any]
    expected: Any


class TaskSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    title: str
    category: str
    difficulty: str
    summary: str
    instructions: str
    function_name: str
    signature: str
    starter_code: str
    reference_code: str = Field(exclude=True)
    tests: tuple[TestVector, ...] = Field(exclude=True)

    def public_dict(self, *, include_instructions: bool = True) -> dict[str, Any]:
        excluded = {"reference_code", "tests"}
        if not include_instructions:
            excluded.update({"instructions", "starter_code"})
        return self.model_dump(exclude=excluded)


class CaseStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"


class RunStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    TIMEOUT = "timeout"


class CaseResult(BaseModel):
    name: str
    status: CaseStatus
    duration_ms: float
    expected: Any = None
    actual: Any = None
    error: str | None = None
    stdout: str = ""


class EvaluationResult(BaseModel):
    status: RunStatus
    duration_ms: float
    passed_cases: int
    total_cases: int
    cases: list[CaseResult]
    runner: str
    error: str | None = None


class RunCreate(BaseModel):
    task_id: str
    code: str = Field(min_length=1, max_length=30_000)


class RunRecord(EvaluationResult):
    id: str
    task_id: str
    task_title: str
    created_at: datetime

    @staticmethod
    def now() -> datetime:
        return datetime.now(timezone.utc)

