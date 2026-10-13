from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .models import RunRecord


class RunStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    task_title TEXT NOT NULL,
                    status TEXT NOT NULL,
                    duration_ms REAL NOT NULL,
                    passed_cases INTEGER NOT NULL,
                    total_cases INTEGER NOT NULL,
                    runner TEXT NOT NULL,
                    error TEXT,
                    cases_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute("CREATE INDEX IF NOT EXISTS runs_created_at ON runs(created_at DESC)")

    def save(self, record: RunRecord) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO runs (
                    id, task_id, task_title, status, duration_ms, passed_cases,
                    total_cases, runner, error, cases_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    record.task_id,
                    record.task_title,
                    record.status.value,
                    record.duration_ms,
                    record.passed_cases,
                    record.total_cases,
                    record.runner,
                    record.error,
                    json.dumps([case.model_dump(mode="json") for case in record.cases]),
                    record.created_at.isoformat(),
                ),
            )

    def get(self, run_id: str) -> RunRecord | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        return self._record(row) if row else None

    def list(self, limit: int = 30) -> list[RunRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM runs ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [self._record(row) for row in rows]

    def summary(self) -> dict[str, float | int]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS total,
                       COALESCE(SUM(CASE WHEN status = 'passed' THEN 1 ELSE 0 END), 0) AS passed,
                       COALESCE(AVG(duration_ms), 0) AS average_ms
                FROM runs
                """
            ).fetchone()
        total = int(row["total"])
        passed = int(row["passed"])
        return {
            "total_runs": total,
            "passed_runs": passed,
            "pass_rate": round(passed / total, 4) if total else 0,
            "average_duration_ms": round(float(row["average_ms"]), 2),
        }

    @staticmethod
    def _record(row: sqlite3.Row) -> RunRecord:
        return RunRecord.model_validate(
            {
                **dict(row),
                "cases": json.loads(row["cases_json"]),
            }
        )

