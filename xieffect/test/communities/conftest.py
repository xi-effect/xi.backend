from __future__ import annotations

from collections.abc import Callable

from flask_fullstack import SocketIOTestClient, FlaskTestClient, dict_reduce
from pytest import fixture

from common import db
from common.users_db import User
from communities.base import (
    Participant,
    PermissionType,
    ParticipantRole,
    Role,
    RolePermission,
)
from communities.base.meta_db import Community
from communities.tasks.main_db import Task
from test.conftest import delete_by_id

COMMUNITY_DATA: dict = {"name": "test"}


def assert_create_community(
    socketio_client: SocketIOTestClient, community_data: dict
) -> int:
    return socketio_client.assert_emit_ack(
        event_name="new_community",
        data=community_data,
        expected_data=dict(community_data, id=int),
    )["id"]


def find_invite(
    client: FlaskTestClient, community_id: int, invite_id: int
) -> dict | None:
    for data in client.paginate(f"/communities/{community_id}/invitations/"):
        if data["id"] == invite_id:
            return data
    return None


@fixture
def test_community(socketio_client: SocketIOTestClient) -> int:
    # TODO use yield & delete the community after
    return assert_create_community(socketio_client, COMMUNITY_DATA)


@fixture
def community_id(base_user_id) -> int:
    community_id = Community.create(
        name="test_community",
        description="description",
        creator_id=base_user_id,
    ).id
    assert Participant.find_by_ids(community_id, base_user_id) is not None
    yield community_id
    delete_by_id(community_id, Community)


@fixture(params=[User, Community])
def table(request) -> type[User | Community]:
    return request.param


@fixture
def task_maker(base_user_id: int, community_id: int) -> Callable[Task]:
    created: list[int] = []

    def task_maker_inner() -> Task:
        task: Task = Task.create(
            base_user_id, community_id, 1, "test", "description", None, None
        )
        created.append(task.id)
        return task

    yield task_maker_inner

    for task_id in created:
        delete_by_id(task_id, Task)


@fixture
def test_task_id(task_maker: Callable[Task]) -> int:
    task: Task = task_maker()
    return task.id


@fixture(scope="session")
def create_participant_role() -> Callable:
    def create_participant_role_wrapper(
        *permissions: PermissionType, community_id: int, client: FlaskTestClient
    ) -> int:
        user_id = client.get(
            "/home/",
            expected_json={"id": int},
        )["id"]
        role = Role.create(name="test_name", color="CD5C5C", community_id=community_id)
        RolePermission.create_bulk(role_id=role.id, permissions=list(permissions))
        participant = Participant.find_by_ids(
            community_id=community_id, user_id=user_id
        )
        assert participant is not None
        ParticipantRole.create(role_id=role.id, participant_id=participant.id)
        db.session.commit()
        return role.id

    return create_participant_role_wrapper


@fixture(scope="session")
def assert_successful_get() -> Callable:
    def assert_successful_get_wrapper(
        client: FlaskTestClient, code, joined: bool
    ) -> None:
        client.get(
            f"/communities/join/{code}/",
            expected_json={
                "joined": joined,
                "authorized": True,
                "community": COMMUNITY_DATA,
            },
        )

    return assert_successful_get_wrapper


@fixture
def create_assert_successful_join(assert_successful_get) -> Callable:
    def assert_successful_join_wrapper(community_id):
        def assert_successful_join_inner(
            client: FlaskTestClient,
            invite_id: int,
            code: str,
            *sio_clients: SocketIOTestClient,
        ) -> None:
            invite = find_invite(client, community_id, invite_id)
            assert invite is not None, "Invitation not found"
            limit_before = invite.get("limit")

            assert_successful_get(client, code, joined=False)
            assert client.post(
                f"/communities/join/{code}/",
                expected_json=COMMUNITY_DATA,
            )

            if limit_before is not None:
                invite = find_invite(client, community_id, invite_id)
                if invite is None:
                    assert limit_before == 1
                else:
                    assert invite["limit"] == limit_before - 1

            for sio in sio_clients:
                sio.assert_only_received("new_community", COMMUNITY_DATA)

        return assert_successful_join_inner

    return assert_successful_join_wrapper


@fixture(scope="session")
def get_role_ids(create_participant_role):
    def wrapper_get_role_ids(client: FlaskTestClient, community_id: int):
        return [
            create_participant_role(
                permission_type="MANAGE_INVITATIONS",
                community_id=community_id,
                client=client,
            )
            for _ in range(3)
        ]

    return wrapper_get_role_ids


@fixture(scope="session")
def get_roles_list_by_ids():
    def wrapper_get_roles_list(
        client: FlaskTestClient, community_id: int, role_ids: list
    ) -> list[dict]:
        """Check the success of getting the list of roles"""
        return [
            dict_reduce(role, "permissions")
            for role in client.get(f"/communities/{community_id}/roles/")
            if role["id"] in role_ids
        ]

    return wrapper_get_roles_list
