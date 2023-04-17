from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta

from flask_fullstack import SocketIOTestClient
from pytest import mark, FixtureRequest

from communities.tasks.main_db import Task, Participant, ParticipantRole
from test.communities.tasks.teacher_test import assert_create_task
from test.conftest import delete_by_id, FlaskTestClient


def test_student_tasks_pagination(
    multi_client: Callable[[str], FlaskTestClient],
    community_id: int,
    test_task_id: int,
):
    filter_data: dict[str, str] = {"filter": "ACTIVE"}
    base_link: str = f"/communities/{community_id}/tasks/"
    student: FlaskTestClient = multi_client("1@user.user")
    student_id: int = student.get(
        "/users/me/profile/", expected_json={"email": "1@user.user"}
    ).get("id")
    Participant.create(community_id, student_id, ParticipantRole.BASE)
    assert len(list(student.paginate(f"{base_link}student/", json=filter_data))) == 0

    task: Task = Task.find_by_id(test_task_id)
    task.opened = datetime.utcnow()
    assert len(list(student.paginate(f"{base_link}student/", json=filter_data))) == 1

    student.paginate(
        base_link,
        json=dict(filter_data, order="created"),
        expected_status=403,
    )


@mark.parametrize(
    (
        "task_id",
        "community_fixture",
        "expected_status",
        "expected_a",
        "expected_json",
        "delta",
    ),
    [
        (
            "test_task_id",
            "community_id",
            403,
            "Permission Denied: Participant not found",
            {},
            0,
        ),
        ("test_task_id", "test_community", 404, Task.not_found_text, {}, 0),
        (None, "test_community", 404, Task.not_found_text, {}, 1),
        (None, "test_community", 200, None, {"name": "test"}, 0),
    ],
    ids=[
        "permission_denied",
        "another_community_task",
        "not_active_task",
        "successful_getting",
    ],
)
def test_student_task_getting(
    multi_client: Callable[[str], FlaskTestClient],
    socketio_client: SocketIOTestClient,
    task_id: str | None,
    community_fixture: str,
    expected_status: int,
    expected_a: str,
    expected_json: dict[str, str],
    delta: int,
    request: FixtureRequest,
):
    community_id: int = request.getfixturevalue(community_fixture)
    task_data: dict[str, int | str] = {
        "community_id": community_id,
        "page_id": 1,
        "name": "test",
    }
    if task_id is None:
        task_id: int = assert_create_task(socketio_client, task_data)
    else:
        task_id: int = request.getfixturevalue(task_id)
    task: Task = Task.find_by_id(task_id)
    task.opened = datetime.utcnow() + timedelta(days=delta)

    student: FlaskTestClient = multi_client("1@user.user")
    if expected_status == 403:
        task_link: str = f"/communities/{community_id}/tasks/{task_id}/"
    else:
        student_id: int = student.get(
            "/users/me/profile/", expected_json={"email": "1@user.user"}
        ).get("id")
        Participant.create(community_id, student_id, ParticipantRole.BASE)
        task_link: str = f"/communities/{community_id}/tasks/student/{task_id}/"

    student.get(
        task_link,
        expected_status=expected_status,
        expected_a=expected_a,
        expected_json=expected_json,
    )

    delete_by_id(task_id, Task)
