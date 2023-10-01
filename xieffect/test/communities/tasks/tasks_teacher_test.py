from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

import pytest
from flask_fullstack import dict_cut, SocketIOTestClient

from communities.base.meta_db import Community
from communities.tasks.main_db import Task
from test.conftest import delete_by_id, FlaskTestClient
from users.users_db import User


@pytest.fixture()
def task_ids(
    test_community: int,
    task_id: int,
) -> dict[str, int]:
    return {
        "community_id": test_community,
        "task_id": task_id,
    }


def test_create_task(
    client: FlaskTestClient,
    socketio_client: SocketIOTestClient,
    test_community: int,
    file_id: int,
):
    task_data: dict[str, Any] = {
        "community_id": test_community,
        "page_id": 1,
        "name": "test task",
        "files": [file_id],
    }
    created_task_id: int = socketio_client.assert_emit_ack(
        event_name="new_task",
        data=task_data,
        expected_data=dict_cut(task_data, "page_id", "name"),
    ).get("id")

    client.get(
        f"/communities/{test_community}/tasks/{created_task_id}/",
        expected_json={
            "name": task_data["name"],
            "files": [{"id": file_id}],
        },
    )
    delete_by_id(created_task_id, Task)


def test_get_wrong_task(
    client: FlaskTestClient,
    client_community_id: int,
    task_id: int,
):
    client.get(
        f"/communities/{client_community_id}/tasks/{task_id}/",
        expected_a=Task.not_found_text,
        expected_status=404,
    )


@pytest.mark.parametrize(
    "update_data",
    [
        pytest.param({"name": "update", "description": "task", "files": []}, id="full"),
        pytest.param({"name": "second_update"}, id="partial"),
    ],
)
def test_update_task(
    client: FlaskTestClient,
    socketio_client: SocketIOTestClient,
    task_id: int,
    test_community: int,
    task_ids: dict[str, int],
    update_data: dict[str, Any],
):
    socketio_client.assert_emit_ack(
        event_name="update_task",
        data={**task_ids, **update_data},
        expected_data=update_data,
    )

    client.get(
        f"/communities/{test_community}/tasks/{task_id}/",
        expected_json=update_data,
    )


def test_delete_task(
    client: FlaskTestClient,
    socketio_client: SocketIOTestClient,
    task_id: int,
    test_community: int,
    task_ids,
):
    socketio_client.assert_emit_success(event_name="delete_task", data=task_ids)

    client.get(
        f"/communities/{test_community}/tasks/{task_id}/",
        expected_status=404,
        expected_a=Task.not_found_text,
    )


@pytest.mark.parametrize(
    ("entry_filter", "entry_order", "count"),
    [
        pytest.param("ALL", "CREATED", 2, id="get_all_tasks"),
        pytest.param("ACTIVE", "OPENED", 0, id="get_only_active"),
    ],
)
def test_teacher_tasks_pagination(
    entry_filter: str,
    entry_order: str,
    count: int,
    test_community: int,
    client: FlaskTestClient,
    task_maker: Callable[[], Task],
):
    json_data: dict[str, str] = {"filter": entry_filter, "order": entry_order}
    base_link: str = f"/communities/{test_community}/tasks/"

    created: list[int] = [task_maker().id for _ in range(2)]
    assert len(list(client.paginate(base_link, json=json_data))) == count

    if entry_filter == "ACTIVE":
        for task in created:
            task: Task = Task.find_by_id(task)
            task.opened = datetime.utcnow()
            count += 1

    task_list: list[dict] = list(client.paginate(base_link, json=json_data))
    assert task_list[count - 1].get("id") == created[-1]
    assert len(task_list) == count


def test_update_foreign_task(
    socketio_client: SocketIOTestClient,
    client_community_id: int,
    task_id: int,
):
    socketio_client.assert_emit_ack(
        event_name="update_task",
        data={
            "name": "new",
            "community_id": client_community_id,
            "task_id": task_id,
        },
        expected_code=404,
        expected_message=Task.not_found_text,
    )


def test_delete_foreign_task(
    socketio_client: SocketIOTestClient,
    client_community_id: int,
    task_id: int,
):
    socketio_client.assert_emit_ack(
        event_name="delete_task",
        data={
            "community_id": client_community_id,
            "task_id": task_id,
        },
        expected_code=404,
        expected_message=Task.not_found_text,
    )


def test_task_constraints(
    table: type[User | Community],
    base_client_task_id: int,
    base_user_id: int,
    community_id: int,
):
    delete_by_id(base_user_id if (table == User) else community_id, table)
    assert Task.find_by_id(base_client_task_id) is None
