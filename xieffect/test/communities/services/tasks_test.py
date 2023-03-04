from __future__ import annotations

from collections.abc import Callable

from flask.testing import FlaskClient
from flask_fullstack import check_code, dict_equal
from pytest import fixture

from common import open_file, User
from common.testing import SocketIOTestClient
from communities.base import Community
from communities.services.tasks_db import Task
from test.conftest import delete_by_id
from test.vault_test import create_file


@fixture
def file_id(client: FlaskClient) -> int:
    with open_file("xieffect/test/json/test-1.json", "rb") as f:
        contents: bytes = f.read()
    return check_code(
        client.post(
            "/files/",
            content_type="multipart/form-data",
            data={"file": create_file("task-file", contents)},
        )
    ).get("id")


def assert_create_task(socketio_client: SocketIOTestClient, task_data: dict) -> dict:
    result_data = socketio_client.assert_emit_ack("new_task", task_data)
    assert isinstance(result_data, dict)
    assert dict_equal(result_data, task_data, "page_id", "name")
    return result_data


def test_task_crud(
    client: FlaskClient,
    multi_client: Callable[[str], FlaskClient],
    test_community: int,
    file_id: int,
):
    def assert_permission_check(method):
        assert (
            check_code(
                method,
                status_code=403,
            ).get("a")
            == "Permission Denied: Participant not found"
        )

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
        "new_task",
        task_data,
        code=403,
        message="Permission Denied: Participant not found",
    )
    added_task = assert_create_task(owner_sio, task_data)
    task_id = added_task.get("id")
    assert_permission_check(guest.get(f"/communities/{test_community}/tasks/{task_id}"))

    updated_task_data = {
        "community_id": test_community,
        "task_id": task_id,
        "name": "updated name",
        "description": "added description",
    }
    guest_sio.assert_emit_ack(
        "update_task",
        updated_task_data,
        code=403,
        message="Permission Denied: Participant not found",
    )
    owner_sio.assert_emit_success("update_task", updated_task_data)
    response = check_code(client.get(f"/communities/{test_community}/tasks/{task_id}/"))
    assert isinstance(response, dict)
    assert dict_equal(response, updated_task_data, "name", "description")
    files = response.get("files")
    assert isinstance(files, list)
    assert len(files) != 0
    file = files[0]
    assert isinstance(file, dict)
    assert file.get("id") == file_id

    updated_task_data["files"] = []
    owner_sio.assert_emit_success("update_task", updated_task_data)
    response = check_code(client.get(f"/communities/{test_community}/tasks/{task_id}/"))
    files = response.get("files")
    assert isinstance(files, list)
    assert len(files) == 0

    delete_task_data = {"community_id": test_community, "task_id": task_id}
    guest_sio.assert_emit_ack(
        "delete_task",
        delete_task_data,
        code=403,
        message="Permission Denied: Participant not found",
    )
    owner_sio.assert_emit_success("delete_task", delete_task_data)
    response = check_code(
        client.get(f"/communities/{test_community}/tasks/{task_id}/"), status_code=404
    ).get("a")
    assert response == "Task not found"


def test_tasks_pagination(
    client: FlaskClient, socketio_client: SocketIOTestClient, test_community: int
):
    pagination = {"counter": 0}
    task_data = {
        "community_id": test_community,
        "page_id": 1,
        "name": "New task name",
    }

    response = check_code(
        client.get(f"/communities/{test_community}/tasks/", json=pagination)
    )
    assert isinstance(response, dict)
    assert isinstance(response.get("results"), list)
    assert len(response.get("results")) == 0

    added_task = assert_create_task(socketio_client, task_data)

    response = check_code(
        client.get(f"/communities/{test_community}/tasks/", json=pagination)
    )
    assert isinstance(response, dict)
    tasks = response.get("results")
    assert isinstance(tasks, list)
    assert len(tasks) != 0
    assert dict_equal(tasks[0], added_task)


def test_task_create_with_wrong_files(
    socketio_client: SocketIOTestClient, test_community: int
):
    task_data = {
        "community-id": test_community,
        "page-id": 1,
        "name": "test task",
        "files": [12354],
    }
    socketio_client.assert_emit_ack(
        "new_task", task_data, code=404, message="File not found"
    )

    task_data["files"] = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
    socketio_client.assert_emit_ack(
        "new_task", task_data, code=400, message="Too many files"
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
