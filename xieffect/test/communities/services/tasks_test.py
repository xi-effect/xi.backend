from __future__ import annotations

from collections.abc import Callable

from flask_fullstack import dict_cut, SocketIOTestClient, assert_contains
from flask_fullstack.utils.kebabs import dekebabify
from pytest import fixture

from common import open_file, User
from communities.base import Community
from communities.services.tasks_db import Task
from test.conftest import delete_by_id, FlaskTestClient
from test.vault_test import create_file


@fixture
def file_id(client: FlaskTestClient) -> int:
    with open_file("xieffect/test/json/test-1.json", "rb") as f:
        contents: bytes = f.read()
    return client.post(
        "/files/",
        content_type="multipart/form-data",
        data={"file": create_file("task-file", contents)},
        expected_json={"id": int},
    )["id"]


def assert_create_task(socketio_client: SocketIOTestClient, task_data: dict) -> dict:
    return socketio_client.assert_emit_ack(
        event_name="new_task",
        data=task_data,
        expected_data=dict_cut(task_data, "page_id", "name"),
    )


def test_task_crud(
    client: FlaskTestClient,
    multi_client: Callable[[str], FlaskTestClient],
    test_community: int,
    file_id: int,
):
    task_data = {
        "community_id": test_community,
        "page_id": 1,
        "name": "test task",
        "files": [file_id],
    }
    owner_sio = SocketIOTestClient(client)
    guest = multi_client("1@user.user")
    guest_sio = SocketIOTestClient(guest)

    guest_sio.assert_emit_ack(
        event_name="new_task",
        data=task_data,
        expected_code=403,
        expected_message="Permission Denied: Participant not found",
    )
    added_task = assert_create_task(owner_sio, task_data)
    task_id = added_task.get("id")
    guest.get(
        f"/communities/{test_community}/tasks/{task_id}/",
        expected_a="Permission Denied: Participant not found",
        expected_status=403,
    )

    updated_task_data = {
        "community_id": test_community,
        "task_id": task_id,
        "name": "updated name",
        "description": "added description",
    }
    guest_sio.assert_emit_ack(
        event_name="update_task",
        data=updated_task_data,
        expected_code=403,
        expected_message="Permission Denied: Participant not found",
    )
    owner_sio.assert_emit_success("update_task", updated_task_data)
    client.get(
        f"/communities/{test_community}/tasks/{task_id}/",
        expected_json={
            "name": updated_task_data["name"],
            "description": updated_task_data["description"],
            "files": [{"id": file_id}],
        },
    )

    updated_task_data["files"] = []
    owner_sio.assert_emit_success("update_task", updated_task_data)
    client.get(
        f"/communities/{test_community}/tasks/{task_id}/",
        expected_json={"files": []},
    )

    delete_task_data = {"community_id": test_community, "task_id": task_id}
    guest_sio.assert_emit_ack(
        event_name="delete_task",
        data=delete_task_data,
        expected_code=403,
        expected_message="Permission Denied: Participant not found",
    )
    owner_sio.assert_emit_success("delete_task", delete_task_data)
    client.get(
        f"/communities/{test_community}/tasks/{task_id}/",
        expected_status=404,
        expected_a="Task not found",
    )


def test_tasks_pagination(
    client: FlaskTestClient, socketio_client: SocketIOTestClient, test_community: int
):
    assert len(list(client.paginate(f"/communities/{test_community}/tasks/"))) == 0

    task_data = {
        "page_id": 1,
        "name": "New task name",
    }
    added_task = assert_create_task(
        socketio_client, dict(task_data, community_id=test_community)
    )
    assert_contains(added_task, task_data)

    tasks = list(client.paginate(f"/communities/{test_community}/tasks/"))
    assert len(tasks) == 1
    assert_contains(dekebabify(tasks[0]), task_data)


def test_task_create_with_wrong_files(
    socketio_client: SocketIOTestClient,
    test_community: int,
):
    task_data = {
        "community-id": test_community,
        "page-id": 1,
        "name": "test task",
        "files": [12354],
    }
    socketio_client.assert_emit_ack(
        event_name="new_task",
        data=task_data,
        expected_code=404,
        expected_message="File not found",
    )

    task_data["files"] = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
    socketio_client.assert_emit_ack(
        event_name="new_task",
        data=task_data,
        expected_code=400,
        expected_message="Too many files",
    )


def test_task_constraints(
    table: type[User | Community],
    base_user_id: int,
    community_id: int,
):
    task_id = Task.create(base_user_id, community_id, 1, "test", "description").id
    assert isinstance(task_id, int)
    assert Task.find_by_id(task_id) is not None

    delete_by_id(base_user_id if (table == User) else community_id, table)
    assert Task.find_by_id(task_id) is None
