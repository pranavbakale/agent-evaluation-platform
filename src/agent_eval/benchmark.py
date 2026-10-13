from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from .catalog import get_catalog
from .models import RunStatus, TaskSpec
from .runner import SandboxRunner, create_runner


@dataclass(frozen=True)
class SeedCase:
    id: str
    task_id: str
    expected: str
    kind: str
    code: str


def build_seed_corpus() -> list[SeedCase]:
    corpus: list[SeedCase] = []
    for index, task in enumerate(get_catalog()):
        valid_variants = [
            task.reference_code,
            task.reference_code + "\n# Equivalent implementation used for repeatability.\n",
        ]
        if index < 10:
            valid_variants.append("# Verified alternative formatting.\n" + task.reference_code)
        for variant_index, code in enumerate(valid_variants, start=1):
            corpus.append(
                SeedCase(
                    id=f"{task.id}-valid-{variant_index}",
                    task_id=task.id,
                    expected="accept",
                    kind="valid",
                    code=code,
                )
            )

        failures = _failure_variants(task)
        for variant_index, (kind, code) in enumerate(failures, start=1):
            corpus.append(
                SeedCase(
                    id=f"{task.id}-failure-{variant_index}",
                    task_id=task.id,
                    expected="reject",
                    kind=kind,
                    code=code,
                )
            )
    return corpus


def _failure_variants(task: TaskSpec) -> list[tuple[str, str]]:
    name = task.function_name
    return [
        ("empty-implementation", f"def {name}(*args):\n    return None\n"),
        ("constant-output", f"def {name}(*args):\n    return 0\n"),
        ("input-echo", f"def {name}(*args):\n    return args[0] if args else None\n"),
        ("runtime-failure", f"def {name}(*args):\n    raise RuntimeError('seeded failure')\n"),
        ("syntax-failure", f"def {name}(*args)\n    return args\n"),
    ]


def run_benchmark(runner: SandboxRunner | None = None) -> dict[str, object]:
    selected_runner = runner or create_runner(os.getenv("RUNNER_BACKEND", "local"))
    tasks = {task.id: task for task in get_catalog()}
    corpus = build_seed_corpus()
    started = time.perf_counter()
    true_positive = false_positive = true_negative = false_negative = 0
    misses: list[dict[str, str]] = []

    for seed in corpus:
        result = selected_runner.evaluate(tasks[seed.task_id], seed.code)
        accepted = result.status == RunStatus.PASSED
        if seed.expected == "reject" and not accepted:
            true_positive += 1
        elif seed.expected == "reject" and accepted:
            false_negative += 1
            misses.append({"case_id": seed.id, "type": "missed_defect"})
        elif seed.expected == "accept" and accepted:
            true_negative += 1
        else:
            false_positive += 1
            misses.append({"case_id": seed.id, "type": "false_positive"})

    precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0
    recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0
    valid_count = sum(seed.expected == "accept" for seed in corpus)
    failure_count = len(corpus) - valid_count
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "runner": selected_runner.name,
        "task_count": len(tasks),
        "case_count": len(corpus),
        "seeded_failures": failure_count,
        "valid_cases": valid_count,
        "true_positive": true_positive,
        "false_positive": false_positive,
        "true_negative": true_negative,
        "false_negative": false_negative,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "duration_ms": round((time.perf_counter() - started) * 1000, 2),
        "exceptions": misses,
        "seed_index": [
            {key: value for key, value in asdict(seed).items() if key != "code"} for seed in corpus
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the deterministic verifier benchmark.")
    parser.add_argument("--write", type=Path, help="Write the JSON report to this path.")
    parser.add_argument("--minimum-precision", type=float, default=0.0)
    parser.add_argument("--minimum-recall", type=float, default=0.0)
    args = parser.parse_args()

    report = run_benchmark()
    rendered = json.dumps(report, indent=2)
    print(rendered)
    if args.write:
        args.write.parent.mkdir(parents=True, exist_ok=True)
        args.write.write_text(rendered + "\n", encoding="utf-8")
    if report["precision"] < args.minimum_precision or report["recall"] < args.minimum_recall:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

