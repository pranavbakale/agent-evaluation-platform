from agent_eval.benchmark import build_seed_corpus


def test_seed_corpus_has_expected_balance_and_unique_ids() -> None:
    corpus = build_seed_corpus()
    assert len(corpus) == 150
    assert len({case.id for case in corpus}) == 150
    assert sum(case.expected == "reject" for case in corpus) == 100
    assert sum(case.expected == "accept" for case in corpus) == 50


def test_every_task_has_five_distinct_failure_patterns() -> None:
    corpus = build_seed_corpus()
    failures_by_task: dict[str, set[str]] = {}
    for case in corpus:
        if case.expected == "reject":
            failures_by_task.setdefault(case.task_id, set()).add(case.kind)
    assert len(failures_by_task) == 20
    assert all(len(patterns) == 5 for patterns in failures_by_task.values())

