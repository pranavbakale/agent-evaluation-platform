# Agent Evaluation Platform

This project is a small evaluation control room for Python coding tasks. It gives a reviewer a repeatable way to run a submission, inspect every check that contributed to the verdict, and see whether changes to a task or verifier introduced a regression.

The platform contains 20 tasks, 100 intentionally broken submissions, and 50 valid submissions. The seeded corpus is run in CI to measure verifier precision and recall. Every interactive run is stored with its timing, runner, case results, captured output, and error details.

## What is included

- A responsive browser interface with a task library, code workspace, trace viewer, run history, and verifier-quality report
- 20 Python tasks covering strings, collections, numbers, control flow, and common algorithms
- Deterministic case checks with expected and observed values
- Docker isolation with no network, a read-only filesystem, dropped capabilities, and CPU, memory, and process limits
- A local subprocess runner for development and CI environments where Docker is unavailable
- SQLite persistence for evaluation traces
- A reproducible 150-case verifier benchmark
- Pytest coverage across the catalog, runner, API, storage, and benchmark corpus
- GitHub Actions jobs for unit tests, the seeded benchmark, and a Docker isolation smoke test

## Quick start with Docker

Docker is the recommended way to run the complete application because submitted code is then evaluated in a separate restricted container.

```bash
docker compose up --build
```

Open [http://localhost:8000](http://localhost:8000). The API reference is available at [http://localhost:8000/api/docs](http://localhost:8000/api/docs).

If port 8000 is already in use, choose another host port with `APP_PORT=8010 docker compose up --build`.

Run `docker compose down` when finished. Evaluation history is kept in `data/evaluations.db`.

## Local development

Create the environment and install the package:

```bash
make setup
```

Build the lightweight runner image once, then start the development server:

```bash
docker build -f Dockerfile.runner -t agent-eval-runner:local .
make dev
```

The application uses the Docker runner when both the daemon and runner image are available. Otherwise, the `auto` setting falls back to a restricted local subprocess so the interface remains usable. The local runner is intended for trusted development fixtures only; it is not a security boundary for untrusted submissions.

Runner selection can be explicit:

```bash
RUNNER_BACKEND=docker agent-eval
RUNNER_BACKEND=local agent-eval
```

## Using the platform

1. Open **Task library** and choose an exercise.
2. Write the requested function in the code workspace.
3. Select **Run evaluation** or press `Cmd/Ctrl + Enter`.
4. Inspect the verdict and each case's expected value, observed value, timing, and error.
5. Open **Run history** to revisit saved traces, or **Verifier quality** to inspect the benchmark summary.

The task API does not return hidden cases or reference implementations. Those stay on the service side and are only passed into the short-lived evaluation workspace.

## Verifier benchmark

The benchmark contains five known failure patterns per task:

- empty implementation
- constant output
- input echo
- forced runtime failure
- syntax failure

The 50 valid cases are equivalent correct implementations distributed across the task catalog. Together they make it possible to count false positives and missed defects rather than treating a green test run as sufficient evidence.

Run the benchmark and refresh its committed report with:

```bash
make validate
```

The command exits unsuccessfully when the configured quality threshold is missed. CI requires both precision and recall to remain at `1.0` for the seeded corpus.

## Tests

```bash
make test
```

For the Docker-specific smoke test:

```bash
make test-docker
```

## Architecture

```text
Browser UI
    │
    ▼
FastAPI service ─────── SQLite trace store
    │
    ├── task catalog and deterministic verifier
    │
    └── sandbox runner
          ├── Docker container (normal operation)
          └── restricted subprocess (trusted local development)
```

The service writes a candidate module, a generated harness, and a task-specific input file into a temporary directory. The runner mounts that directory read-only, executes the harness with a fixed hash seed and a hard timeout, and returns one structured result marker. Candidate output is captured separately, so printing cannot corrupt the runner protocol.

The storage layer opens short SQLite connections rather than sharing a connection across request threads. WAL mode keeps reads responsive while runs are being saved. The frontend uses the JSON API directly and has no build step or external browser dependencies.

## Project layout

```text
src/agent_eval/
  benchmark.py       seeded precision and recall benchmark
  catalog.py         task specifications and deterministic vectors
  main.py            HTTP API and static application entry point
  models.py          request, result, and trace models
  runner.py          Docker and local execution backends
  service.py         evaluation orchestration
  store.py           SQLite trace persistence
  static/            browser interface
benchmarks/           committed validation report
tests/                unit, API, corpus, and isolation tests
```

## API summary

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Service and runner status |
| `GET` | `/api/tasks` | Public task catalog |
| `GET` | `/api/tasks/{id}` | Task instructions and starter code |
| `POST` | `/api/runs` | Evaluate and persist a submission |
| `GET` | `/api/runs` | Recent run history |
| `GET` | `/api/runs/{id}` | One complete trace |
| `GET` | `/api/overview` | Dashboard totals and quality metrics |
| `GET` | `/api/validation` | Latest seeded benchmark report |

## Design choices

The platform deliberately favors boring, inspectable parts. Task inputs are data, the harness is generated from one small template, the result protocol is a single JSON marker, and the trace store is SQLite. That makes failures easy to reproduce on a laptop and avoids hiding verifier behavior behind a complicated job system.

The browser client is plain HTML, CSS, and JavaScript. For a focused internal tool, this keeps startup fast and makes the application distributable as one Python package without a second build pipeline.

## What I would do differently in production

I would move execution out of the web process and place jobs on a durable queue with independently scaled workers. The container boundary would be strengthened with a purpose-built sandbox such as gVisor or microVMs, per-tenant quotas, signed runner images, tighter syscall policies, and automatic cleanup verification. I would also replace SQLite with PostgreSQL, put large trace artifacts in object storage, add authentication and role-based access, encrypt retained submissions, and define retention policies.

Task and verifier definitions would become immutable, versioned records so every historical verdict could be replayed against the exact original inputs. Benchmark reports would be tied to those versions and promoted through environments as release artifacts. Finally, I would add distributed tracing, queue and sandbox saturation metrics, audit logs, rate limiting, failure alerting, backup testing, and a staged rollout process for verifier changes.
