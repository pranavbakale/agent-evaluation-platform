.PHONY: setup dev test test-docker validate docker-up docker-down

setup:
	python3 -m venv .venv
	.venv/bin/python -m pip install --upgrade pip
	.venv/bin/pip install -e ".[dev]"

dev:
	RUNNER_BACKEND=auto .venv/bin/uvicorn agent_eval.main:app --reload --host 0.0.0.0 --port 8000

test:
	RUNNER_BACKEND=local .venv/bin/pytest

test-docker:
	docker build -f Dockerfile.runner -t agent-eval-runner:local .
	RUNNER_BACKEND=docker .venv/bin/pytest -m docker

validate:
	RUNNER_BACKEND=local .venv/bin/agent-eval-validate --write benchmarks/validation_report.json

docker-up:
	docker compose up --build

docker-down:
	docker compose down

