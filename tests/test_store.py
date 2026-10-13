from __future__ import annotations

from agent_eval.models import EvaluationResult, RunRecord, RunStatus
from agent_eval.store import RunStore


def sample_record(identifier: str = "run123") -> RunRecord:
    return RunRecord(
        id=identifier,
        task_id="sum-numbers",
        task_title="Sum Numbers",
        created_at=RunRecord.now(),
        status=RunStatus.PASSED,
        duration_ms=12.5,
        passed_cases=4,
        total_cases=4,
        cases=[],
        runner="local",
    )


def test_store_round_trip_and_summary(tmp_path) -> None:
    store = RunStore(tmp_path / "runs.db")
    record = sample_record()
    store.save(record)
    loaded = store.get(record.id)
    assert loaded == record
    assert store.list() == [record]
    assert store.summary() == {
        "total_runs": 1,
        "passed_runs": 1,
        "pass_rate": 1.0,
        "average_duration_ms": 12.5,
    }


def test_store_returns_none_for_unknown_run(tmp_path) -> None:
    store = RunStore(tmp_path / "runs.db")
    assert store.get("missing") is None

