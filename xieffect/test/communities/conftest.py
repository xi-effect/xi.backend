from __future__ import annotations

from collections.abc import Callable

from flask_fullstack import SocketIOTestClient, FlaskTestClient, dict_reduce
from pytest import fixture

from common import db
from communities.base.discussion_db import DiscussionMessage
from communities.base.meta_db import (
    Participant,
    PermissionType,
    ParticipantRole,
    Role,
    RolePermission,
    Community,
)
from test.conftest import delete_by_id
from users.users_db import User

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
    community_id = assert_create_community(socketio_client, COMMUNITY_DATA)
    yield community_id
    delete_by_id(community_id, Community)


@fixture
def community(socketio_client: SocketIOTestClient) -> Community:
    community = Community.find_by_id(
        assert_create_community(socketio_client, COMMUNITY_DATA)
    )
    yield community
    delete_by_id(community.id, Community)


@fixture
def community_id(base_user_id: int) -> int:
    community_id = Community.create(
        name="test_community",
        description="description",
        creator_id=base_user_id,
    ).id
    assert Participant.find_by_ids(community_id, base_user_id) is not None
    yield community_id
    delete_by_id(community_id, Community)


@fixture
def client_community_id(socketio_client: SocketIOTestClient) -> int:
    return assert_create_community(socketio_client, {"name": "client_test"})


@fixture(params=[User, Community])
def table(request) -> type[User | Community]:
    return request.param


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
def create_assert_successful_join(assert_successful_get, client) -> Callable:
    def assert_successful_join_wrapper(community_id):
        def assert_successful_join_inner(
            joiner: FlaskTestClient,
            invite_id: int,
            code: str,
            *sio_clients: SocketIOTestClient,
        ) -> None:
            user_id = joiner.get("/home/")["id"]
            count_before = len(Participant.get_communities_list(user_id=user_id))

            invite = find_invite(client, community_id, invite_id)
            assert invite is not None, "Invitation not found"
            limit_before = invite.get("limit")

            assert_successful_get(joiner, code, joined=False)
            assert joiner.post(
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

            communities_after = Participant.get_communities_list(user_id=user_id)
            assert len(communities_after) == count_before + 1
            assert community_id in {community.id for community in communities_after}

        return assert_successful_join_inner

    return assert_successful_join_wrapper


@fixture(scope="session")
def get_role_ids(create_participant_role):
    def wrapper_get_role_ids(client: FlaskTestClient, community_id: int):
        return [
            create_participant_role(
                PermissionType.MANAGE_INVITATIONS,
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


@fixture
def message_content() -> dict[str, str]:
    return {"test": "content"}


@fixture
def message_id(
    base_user_id: int,
    test_discussion_id: int,
    message_content: dict[str, str],
    test_file_id: int,
) -> int:
    message_id: int = DiscussionMessage.create(
        content=message_content,
        sender_id=base_user_id,
        discussion_id=test_discussion_id,
        file_ids=[test_file_id],
    ).id
    yield message_id
    delete_by_id(message_id, DiscussionMessage)
