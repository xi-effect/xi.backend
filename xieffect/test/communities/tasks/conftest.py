from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pytest import fixture

from communities.tasks.tasks_db import Task
from communities.tasks.tests_db import Test
from test.conftest import delete_by_id


@fixture
def task_data(test_user_id: int, test_community: int) -> dict[str, Any]:
    return {
        "user_id": test_user_id,
        "community_id": test_community,
        "page_id": 1,
        "name": "test",
        "description": "description",
        "opened": None,
        "closed": None,
    }


@fixture
def task_maker(task_data: dict[str, Any]) -> Callable[[], Task]:
    created: list[int] = []

    def task_maker_inner() -> Task:
        task: Task = Task.create(**task_data)
        created.append(task.id)
        return task

    yield task_maker_inner

    for task_id in created:
        delete_by_id(task_id, Task)


@fixture
def task_id(task_maker: Callable[[], Task]) -> int:
    task: Task = task_maker()
    return task.id


@fixture
def test_maker(task_data: dict[str, Any]) -> Callable[[], Test]:
    created: list[int] = []

    def test_maker_inner() -> Test:
        test: Test = Test.create(**task_data)
        created.append(test.id)
        return test

    yield test_maker_inner

    for test_id in created:
        delete_by_id(test_id, Test)


@fixture
def test_id(test_maker: Callable[[], Test]) -> int:
    test: Test = test_maker()
    return test.id


@fixture()
def test_ids(
    test_community: int,
    test_id: int,
) -> dict[str, int]:
    return {
        "community_id": test_community,
        "test_id": test_id,
    }


@fixture
def base_client_data(
    base_user_id: int,
    community_id: int,
    task_data: dict[str, Any],
) -> dict[str, Any]:
    task_data.update(user_id=base_user_id, community_id=community_id)
    return task_data


@fixture
def base_client_test_id(
    base_client_data: dict[str, Any],
) -> int:
    test: Test = Test.create(**base_client_data)
    yield test.id


@fixture
def base_client_task_id(
    base_client_data: dict[str, Any],
) -> int:
    task: Task = Test.create(**base_client_data)
    yield task.id
