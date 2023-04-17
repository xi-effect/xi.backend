from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from flask_fullstack import dict_cut, SocketIOTestClient
from pytest import fixture, mark, FixtureRequest

from common import open_file, User
from communities.base import Community
from communities.tasks.main_db import Task
from test.conftest import delete_by_id, FlaskTestClient
from test.vault_test import create_file
from wsgi import TEST_EMAIL


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


def assert_create_task(socketio_client: SocketIOTestClient, task_data: dict) -> int:
    return socketio_client.assert_emit_ack(
        event_name="new_task",
        data=task_data,
        expected_data=dict_cut(task_data, "page_id", "name"),
    ).get("id")


def test_teacher_task_crud(
    client: FlaskTestClient,
    socketio_client: SocketIOTestClient,
    test_community: int,
    file_id: int,
    test_task_id: int,
):
    task_data: dict[str, int | str | list] = {
        "community_id": test_community,
        "page_id": 1,
        "name": "test task",
        "files": [file_id],
    }
    task_id: int = assert_create_task(socketio_client, task_data)
    client.get(
        f"/communities/{test_community}/tasks/{test_task_id}/",
        expected_a=Task.not_found_text,
        expected_status=404,
    )

    ids_data: dict[str, int] = {"community_id": test_community, "task_id": task_id}
    updated_data: dict[str, int | str | list] = dict(
        **ids_data, name="update", description="test"
    )
    socketio_client.assert_emit_success("update_task", updated_data)
    client.get(
        f"/communities/{test_community}/tasks/{task_id}/",
        expected_json=dict(
            dict_cut(updated_data, "name", "description"),
            files=[{"id": file_id}],
        ),
    )
    updated_data["files"]: list[int] = []
    socketio_client.assert_emit_success("update_task", updated_data)
    client.get(
        f"/communities/{test_community}/tasks/{task_id}/",
        expected_json={"files": updated_data["files"]},
    )

    socketio_client.assert_emit_success("delete_task", ids_data)
    client.get(
        f"/communities/{test_community}/tasks/{task_id}/",
        expected_status=404,
        expected_a=Task.not_found_text,
    )


@mark.parametrize(
    ("entry_filter", "entry_order", "count"),
    [
        ("ALL", "CREATED", 2),
        ("ACTIVE", "OPENED", 0),
    ],
    ids=["get_all_tasks", "get_only_active"],
)
def test_teacher_tasks_pagination(
    entry_filter: str,
    entry_order: str,
    count: int,
    task_maker: Callable[Task],
    community_id: int,
    fresh_client: FlaskTestClient,
):
    json_data: dict[str, str] = {"filter": entry_filter, "order": entry_order}
    base_link: str = f"/communities/{community_id}/tasks/"

    created: list[int] = [task_maker().id for _ in range(2)]
    assert len(list(fresh_client.paginate(base_link, json=json_data))) == count

    if entry_filter == "ACTIVE":
        for task in created:
            task: Task = Task.find_by_id(task)
            task.opened = datetime.utcnow()
            count += 1

    task_list: list[dict] = list(fresh_client.paginate(base_link, json=json_data))
    assert task_list[count - 1].get("id") == created[-1]
    assert len(task_list) == count


@mark.parametrize(
    (
        "event_name",
        "client_email",
        "expected_code",
        "expected_message",
        "data",
        "task_id",
    ),
    [
        ("new_task", TEST_EMAIL, 404, "File not found", {"files": [12345]}, None),
        (
            "new_task",
            TEST_EMAIL,
            400,
            "Too many files",
            {"files": list(range(11))},
            None,
        ),
        (
            "new_task",
            "1@user.user",
            403,
            "Permission Denied: Participant not found",
            {"files": [12345]},
            None,
        ),
        (
            "update_task",
            TEST_EMAIL,
            404,
            Task.not_found_text,
            {"name": "new"},
            "test_task_id",
        ),
        ("delete_task", TEST_EMAIL, 404, Task.not_found_text, {}, "test_task_id"),
    ],
    ids=[
        "file_not_found",
        "too_many_files",
        "permission_denied",
        "update_foreign_task",
        "delete_foreign_task",
    ],
)
def test_task_sio_errors(
    multi_client: Callable[[str], FlaskTestClient],
    test_community: int,
    event_name: str,
    client_email: str,
    expected_code: int,
    expected_message: str,
    data: dict[str, list | str],
    task_id: str,
    request: FixtureRequest,
):
    client: FlaskTestClient = multi_client(client_email)
    client_sio: SocketIOTestClient = SocketIOTestClient(client)
    task_data: dict[str, list | str | int] = dict(**data, community_id=test_community)
    if task_id is not None:
        task_id: int = request.getfixturevalue(task_id)
        task_data: dict[str, str | int] = dict(**task_data, task_id=task_id)
    else:
        task_data: dict[str, list | int] = dict(**task_data, name="test", page_id=1)
    client_sio.assert_emit_ack(
        event_name=event_name,
        data=task_data,
        expected_code=expected_code,
        expected_message=expected_message,
    )


def test_task_constraints(
    table: type[User | Community],
    test_task_id: int,
    base_user_id: int,
    community_id: int,
):
    delete_by_id(base_user_id if (table == User) else community_id, table)
    assert Task.find_by_id(test_task_id) is None
