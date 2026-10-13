from agent_eval.catalog import get_catalog, get_task


def test_catalog_contains_twenty_unique_tasks() -> None:
    tasks = get_catalog()
    assert len(tasks) == 20
    assert len({task.id for task in tasks}) == 20
    assert len({task.function_name for task in tasks}) == 20
    assert all(task.tests for task in tasks)


def test_public_task_never_exposes_verifier_material() -> None:
    task = get_catalog()[0]
    public = task.public_dict()
    assert "reference_code" not in public
    assert "tests" not in public
    assert public["starter_code"].startswith("def ")


def test_unknown_task_returns_none() -> None:
    assert get_task("not-a-task") is None

