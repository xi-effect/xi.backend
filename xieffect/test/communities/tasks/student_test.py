from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta

from pytest import mark, fixture, param

from common import db
from communities.base.meta_db import Participant
from communities.tasks.tasks_db import Task
from test.conftest import FlaskTestClient


@fixture
def student(
    multi_client: Callable[[str], FlaskTestClient], test_community: int
) -> FlaskTestClient:
    student: FlaskTestClient = multi_client("1@user.user")
    student_id: int = student.get(
        "/users/me/profile/",
        expected_json={"email": "1@user.user", "id": int},
    )["id"]
    participant = Participant.create(test_community, student_id)
    db.session.commit()

    yield student

    participant.delete()
    db.session.commit()


def test_student_tasks_pagination(
    student: FlaskTestClient,
    test_community: int,
    task_id: int,
):
    filter_data: dict[str, str] = {"filter": "ACTIVE"}
    base_link: str = f"/communities/{test_community}/tasks/"

    assert len(list(student.paginate(f"{base_link}student/", json=filter_data))) == 0

    task: Task = Task.find_by_id(task_id)
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
    task_maker: Callable[[], Task],
    test_community: int,
    expected_status: int,
    expected_a: str,
    expected_json: dict[str, str],
    delta: int,
):
    task: Task = task_maker()
    task.opened = datetime.utcnow() + timedelta(days=delta)
    student.get(
        f"/communities/{test_community}/tasks/student/{task.id}/",
        expected_status=expected_status,
        expected_a=expected_a,
        expected_json=expected_json,
    )
