from __future__ import annotations

from fastapi.testclient import TestClient

from agent_eval.main import create_app
from agent_eval.runner import LocalProcessRunner


def client(tmp_path) -> TestClient:
    return TestClient(create_app(database_path=tmp_path / "api.db", runner=LocalProcessRunner()))


def test_health_and_catalog_endpoints(tmp_path) -> None:
    with client(tmp_path) as test_client:
        health = test_client.get("/api/health")
        assert health.status_code == 200
        assert health.json()["runner"] == "local"

        tasks = test_client.get("/api/tasks")
        assert tasks.status_code == 200
        assert len(tasks.json()) == 20
        assert "starter_code" not in tasks.json()[0]

        detail = test_client.get("/api/tasks/sum-numbers")
        assert detail.status_code == 200
        assert detail.json()["signature"] == "sum_numbers(values)"
        assert "tests" not in detail.json()


def test_create_and_retrieve_run(tmp_path) -> None:
    code = "def sum_numbers(values):\n    return sum(values)\n"
    with client(tmp_path) as test_client:
        created = test_client.post("/api/runs", json={"task_id": "sum-numbers", "code": code})
        assert created.status_code == 201
        record = created.json()
        assert record["status"] == "passed"
        assert record["passed_cases"] == 4

        listed = test_client.get("/api/runs")
        assert listed.status_code == 200
        assert listed.json()[0]["id"] == record["id"]

        fetched = test_client.get(f"/api/runs/{record['id']}")
        assert fetched.status_code == 200
        assert fetched.json() == record


def test_not_found_and_validation_errors(tmp_path) -> None:
    with client(tmp_path) as test_client:
        assert test_client.get("/api/tasks/missing").status_code == 404
        assert test_client.get("/api/runs/missing").status_code == 404
        assert test_client.post("/api/runs", json={"task_id": "missing", "code": "pass"}).status_code == 404
        assert test_client.post("/api/runs", json={"task_id": "sum-numbers", "code": ""}).status_code == 422


def test_overview_and_frontend_are_available(tmp_path) -> None:
    with client(tmp_path) as test_client:
        overview = test_client.get("/api/overview")
        assert overview.status_code == 200
        assert overview.json()["catalog"]["tasks"] == 20
        assert overview.json()["validation"]["case_count"] == 150

        page = test_client.get("/")
        assert page.status_code == 200
        assert "Agent Evaluation" in page.text
        assert "/static/app.js" in page.text

