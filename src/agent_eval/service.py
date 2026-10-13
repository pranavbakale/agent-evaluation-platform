from __future__ import annotations

import logging
from uuid import uuid4

from .catalog import get_task
from .models import RunRecord
from .runner import SandboxRunner
from .store import RunStore

logger = logging.getLogger("agent_eval")


class EvaluationService:
    def __init__(self, runner: SandboxRunner, store: RunStore) -> None:
        self.runner = runner
        self.store = store

    def evaluate(self, task_id: str, code: str) -> RunRecord:
        task = get_task(task_id)
        if task is None:
            raise KeyError(task_id)

        result = self.runner.evaluate(task, code)
        record = RunRecord(
            id=uuid4().hex[:12],
            task_id=task.id,
            task_title=task.title,
            created_at=RunRecord.now(),
            **result.model_dump(),
        )
        self.store.save(record)
        logger.info(
            "evaluation_complete run_id=%s task_id=%s status=%s passed=%s total=%s duration_ms=%s runner=%s",
            record.id,
            record.task_id,
            record.status,
            record.passed_cases,
            record.total_cases,
            record.duration_ms,
            record.runner,
        )
        return record

