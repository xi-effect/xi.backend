from __future__ import annotations

from typing import Callable

from flask.testing import FlaskClient
from flask_socketio import SocketIOTestClient
from pytest import fixture

from __lib__.flask_fullstack import check_code, dict_equal
from .community_base_test import assert_create_community
from .vault_test import create_file

COMMUNITY_DATA = {
    "name": "New community",
    "description": "Community for tasks",
}
FILENAME = "sample-module.json"


@fixture
def community_id(socketio_client: SocketIOTestClient) -> int:
    return assert_create_community(socketio_client, COMMUNITY_DATA)


@fixture
def file_id(client: FlaskClient) -> int:
    with open(f"test/json/{FILENAME}", "rb") as f:
        contents: bytes = f.read()
    return check_code(
        client.post(
            "/files/",
            content_type="multipart/form-data",
            data={"file": create_file(FILENAME, contents)},
        )
    ).get("id", None)


def test_get_create_tasks(client: FlaskClient, community_id):
    pagination = {"counter": 0}
    task_data = {
        "page_id": 1,
        "name": "New task name",
    }

    response = check_code(
        client.get(f"/communities/{community_id}/tasks/", json=pagination)
    )
    assert isinstance(response, dict)
    assert isinstance(response.get("results", None), list)
    assert len(response.get("results", None)) == 0

    added_task = check_code(
        (client.post(f"/communities/{community_id}/tasks/", json=task_data))
    )

    assert dict_equal(added_task, task_data, "name")

    response = check_code(
        client.get(f"/communities/{community_id}/tasks/", json=pagination)
    )
    assert isinstance(response, dict)
    tasks = response.get("results", None)
    assert isinstance(tasks, list)
    assert len(tasks) != 0
    assert dict_equal(tasks[0], added_task)


def test_task_with_wrong_files(client: FlaskClient, community_id):
    task_data = {"page_id": 1, "name": "test task", "files": 1}

    response = check_code(
        client.post(f"/communities/{community_id}/tasks/", json=task_data),
        status_code=404,
    ).get("a", None)
    assert response == "File not found"

    task_data["files"] = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
    response = check_code(
        client.post(f"/communities/{community_id}/tasks/", json=task_data),
        status_code=400,
    ).get("a", None)
    assert response == "Too many files"


def test_task_operations(
    client: FlaskClient,
    multi_client: Callable[[str], FlaskClient],
    community_id,
    file_id,
):
    task_data = {"page_id": 1, "name": "test task", "files": file_id}
    guest = multi_client("1@user.user")

    response = check_code(
        guest.post(f"/communities/{community_id}/tasks/", json=task_data), status_code=403
    ).get("a", None)
    assert response == "Permission denied: Not a member"

    response = check_code(
        client.post(f"/communities/{community_id}/tasks/", json=task_data)
    )
    assert isinstance(response, dict)
    task_id = response.get("id", None)

    response = check_code(
        (guest.get(f"/communities/{community_id}/tasks/{task_id}")), status_code=403
    ).get("a", None)
    assert response == "Permission denied: Not a member"

    updated_task_data = {
        "name": "updated name",
        "description": "added description",
        "files": [],
    }

    response = check_code(
        guest.put(
            f"/communities/{community_id}/tasks/{task_id}/", json=updated_task_data
        ),
        status_code=403,
    ).get("a", None)
    assert response == "Permission denied: Not a member"

    response = check_code(
        client.put(
            f"/communities/{community_id}/tasks/{task_id}/", json=updated_task_data
        )
    ).get("a", None)
    assert response

    response = check_code(client.get(f"/communities/{community_id}/tasks/{task_id}/"))
    assert dict_equal(response, updated_task_data, "name", "description", "files")

    response = check_code(
        guest.delete(f"/communities/{community_id}/tasks/{task_id}/"), status_code=403
    ).get("a", None)
    assert response == "Permission denied: Not a member"

    response = check_code(
        client.delete(f"/communities/{community_id}/tasks/{task_id}/")
    ).get("a", None)
    assert response

    response = check_code(
        client.get(f"/communities/{community_id}/tasks/{task_id}/"), status_code=404
    ).get("a", None)
    assert response == "Task not found"
