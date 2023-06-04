from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta

from pytest import mark, fixture, param

from common import db
from communities.base import Participant
from communities.tasks.main_db import Task
from test.conftest import FlaskTestClient


@fixture
def student(
    multi_client: Callable[[str], FlaskTestClient], community_id: int
) -> FlaskTestClient:
    student: FlaskTestClient = multi_client("1@user.user")
    student_id: int = student.get(
        "/users/me/profile/",
        expected_json={"email": "1@user.user", "id": int},
    )["id"]
    participant = Participant.create(community_id, student_id)
    db.session.commit()

    yield student

    participant.delete()
    db.session.commit()


def test_student_tasks_pagination(
    student: FlaskTestClient,
    community_id: int,
    test_task_id: int,
):
    filter_data: dict[str, str] = {"filter": "ACTIVE"}
    base_link: str = f"/communities/{community_id}/tasks/"

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
        "expected_status",
        "expected_a",
        "expected_json",
        "delta",
    ),
    [
        param(404, Task.not_found_text, {}, 1, id="not_active_task"),
        param(200, None, {"name": "test"}, 0, id="successful_getting"),
    ],
)
def test_student_task_getting(
    student: FlaskTestClient,
    community_id: int,
    base_user_id: int,
    expected_status: int,
    expected_a: str,
    expected_json: dict[str, str],
    delta: int,
):
    task: Task = Task.create(
        user_id=base_user_id,
        community_id=community_id,
        name="test",
        page_id=1,  # TODO remove hardcoding
    )
    task.opened = datetime.utcnow() + timedelta(days=delta)

    student.get(
        f"/communities/{community_id}/tasks/student/{task.id}/",
        expected_status=expected_status,
        expected_a=expected_a,
        expected_json=expected_json,
    )

    task.delete()
