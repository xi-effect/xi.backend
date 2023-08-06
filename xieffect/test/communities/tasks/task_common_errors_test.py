from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from flask_fullstack import SocketIOTestClient
from pytest import fixture

from test.conftest import FlaskTestClient


@dataclass
class FixtureRequest:
    param: str


@fixture(params=["new_task", "new_test"])
def event_name(request: FixtureRequest) -> str:
    return request.param


def test_task_fail_with_nonexistent_file(
    socketio_client: SocketIOTestClient, test_community: int, event_name: str
):
    socketio_client.assert_emit_ack(
        event_name=event_name,
        data={
            "files": [12345],
            "community_id": test_community,
            "name": "test",
            "page_id": 1,
        },
        expected_code=404,
        expected_message="File not found",
    )


def test_task_fail_with_too_many_files(
    socketio_client: SocketIOTestClient, test_community: int, event_name: str
):
    socketio_client.assert_emit_ack(
        event_name=event_name,
        data={
            "files": list(range(11)),
            "community_id": test_community,
            "name": "test",
            "page_id": 1,
        },
        expected_code=400,
        expected_message="Too many files",
    )


def test_task_fail_with_foreign_user(
    multi_client: Callable[[str], FlaskTestClient], test_community: int, event_name: str
):
    foreign_user_email: str = "1@user.user"

    client: FlaskTestClient = multi_client(foreign_user_email)
    client_sio: SocketIOTestClient = SocketIOTestClient(client)

    client_sio.assert_emit_ack(
        event_name=event_name,
        data={
            "files": [12345],
            "community_id": test_community,
            "name": "test",
            "page_id": 1,
        },
        expected_code=403,
        expected_message="Permission Denied: Participant not found",
    )
