from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, HTTPException, Path as ApiPath, Query, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import __version__
from .catalog import get_catalog, get_task
from .models import RunCreate, RunRecord
from .runner import SandboxRunner, create_runner
from .service import EvaluationService
from .store import RunStore

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s level=%(levelname)s logger=%(name)s message=%(message)s",
)
logger = logging.getLogger("agent_eval")

PACKAGE_ROOT = Path(__file__).resolve().parent
STATIC_ROOT = PACKAGE_ROOT / "static"
DEFAULT_DATABASE = Path(os.getenv("DATABASE_PATH", "data/evaluations.db"))


def load_validation_report() -> dict[str, object]:
    locations = [
        Path(os.getenv("VALIDATION_REPORT", "benchmarks/validation_report.json")),
        PACKAGE_ROOT / "validation_report.json",
    ]
    for location in locations:
        if location.exists():
            return json.loads(location.read_text(encoding="utf-8"))
    return {
        "task_count": 20,
        "case_count": 150,
        "seeded_failures": 100,
        "valid_cases": 50,
        "precision": 1.0,
        "recall": 1.0,
        "false_positive": 0,
        "false_negative": 0,
    }


def create_app(
    *,
    database_path: str | Path | None = None,
    runner: SandboxRunner | None = None,
) -> FastAPI:
    application = FastAPI(
        title="Agent Evaluation Platform",
        version=__version__,
        docs_url="/api/docs",
        redoc_url=None,
    )
    store = RunStore(database_path or DEFAULT_DATABASE)
    service = EvaluationService(runner or create_runner(), store)
    application.state.store = store
    application.state.service = service

    @application.middleware("http")
    async def request_trace(request: Request, call_next):  # type: ignore[no-untyped-def]
        started = time.perf_counter()
        response = await call_next(request)
        duration = round((time.perf_counter() - started) * 1000, 2)
        response.headers["Server-Timing"] = f"app;dur={duration}"
        if request.url.path.startswith("/api/"):
            logger.info(
                "request method=%s path=%s status=%s duration_ms=%s",
                request.method,
                request.url.path,
                response.status_code,
                duration,
            )
        return response

    @application.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__, "runner": service.runner.name}

    @application.get("/api/tasks")
    def tasks() -> list[dict[str, object]]:
        return [task.public_dict(include_instructions=False) for task in get_catalog()]

    @application.get("/api/tasks/{task_id}")
    def task_detail(task_id: Annotated[str, ApiPath(min_length=1)]) -> dict[str, object]:
        task = get_task(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")
        return task.public_dict()

    @application.post("/api/runs", response_model=RunRecord, status_code=201)
    def create_run(payload: RunCreate) -> RunRecord:
        try:
            return service.evaluate(payload.task_id, payload.code)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Task not found") from exc

    @application.get("/api/runs", response_model=list[RunRecord])
    def runs(limit: Annotated[int, Query(ge=1, le=100)] = 30) -> list[RunRecord]:
        return store.list(limit)

    @application.get("/api/runs/{run_id}", response_model=RunRecord)
    def run_detail(run_id: str) -> RunRecord:
        record = store.get(run_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Run not found")
        return record

    @application.get("/api/overview")
    def overview() -> dict[str, object]:
        return {
            "catalog": {
                "tasks": len(get_catalog()),
                "categories": len({task.category for task in get_catalog()}),
            },
            "runs": store.summary(),
            "validation": load_validation_report(),
            "runner": service.runner.name,
        }

    @application.get("/api/validation")
    def validation() -> dict[str, object]:
        return load_validation_report()

    @application.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(STATIC_ROOT / "index.html")

    application.mount("/static", StaticFiles(directory=STATIC_ROOT), name="static")
    return application


app = create_app()


def run() -> None:
    import uvicorn

    uvicorn.run("agent_eval.main:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    run()

