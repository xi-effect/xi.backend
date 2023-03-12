from __future__ import annotations

from collections.abc import Callable

from flask.testing import FlaskClient
from flask_fullstack import check_code
from pytest import fixture

from common import db
from common.testing import SocketIOTestClient, dict_equal
from communities.base import (
    Participant,
    PermissionType,
    ParticipantRole,
    Role,
    RolePermission,
    INVITATIONS_PER_REQUEST
)

COMMUNITY_DATA: dict = {"name": "test"}


def assert_create_community(
    socketio_client: SocketIOTestClient, community_data: dict
) -> int:
    result_data = socketio_client.assert_emit_ack("new_community", community_data)
    assert isinstance(result_data, dict)
    assert dict_equal(result_data, community_data, *community_data.keys())

    community_id = result_data.get("id")
    assert isinstance(community_id, int)
    return community_id


def find_invite(list_tester, community_id: int, invite_id: int) -> dict | None:
    index_url = f"/communities/{community_id}/invitations/index/"
    for data in list_tester(index_url, {}, INVITATIONS_PER_REQUEST):
        if data["id"] == invite_id:
            return data
    return None


@fixture
def test_community(socketio_client: SocketIOTestClient) -> int:
    # TODO use yield & delete the community after
    return assert_create_community(socketio_client, COMMUNITY_DATA)


@fixture(scope="session")
def create_participant_role() -> Callable:
    def create_participant_role_wrapper(
        permission_type: PermissionType, community_id: int, client: FlaskClient
    ) -> int:
        response = client.get("/home/")
        user_id = check_code(response, get_json=True)["id"]
        role = Role.create(name="test_name", color="CD5C5C", community_id=community_id)
        RolePermission.create_bulk(role_id=role.id, permissions=[permission_type])
        participant = Participant.find_by_ids(
            community_id=community_id, user_id=user_id
        )
        assert participant is not None
        ParticipantRole.create_bulk(role_ids=[role.id], participant_id=participant.id)
        db.session.commit()
        return role.id

    return create_participant_role_wrapper


@fixture(scope="session")
def assert_successful_get() -> Callable:
    def assert_successful_get_wrapper(client: FlaskClient, code, joined: bool) -> None:
        data = check_code(client.get(f"/communities/join/{code}/"))
        assert data.get("joined") is joined
        assert data.get("authorized") is True

        community = data.get("community")
        assert community is not None
        assert dict_equal(community, COMMUNITY_DATA, *COMMUNITY_DATA.keys())

    return assert_successful_get_wrapper


@fixture
def create_assert_successful_join(assert_successful_get, list_tester) -> Callable:
    def assert_successful_join_wrapper(community_id):
        def assert_successful_join_inner(
            client: FlaskClient,
            invite_id: int,
            code: str,
            *sio_clients: SocketIOTestClient,
        ) -> None:
            invite = find_invite(list_tester, community_id, invite_id)
            assert (
                invite is not None
            ), "Invitation not found inside assert_successful_join"
            limit_before = invite.get("limit")

            assert_successful_get(client, code, joined=False)
            assert dict_equal(
                check_code(client.post(f"/communities/join/{code}/")),
                COMMUNITY_DATA,
                *COMMUNITY_DATA.keys(),
            )

            if limit_before is not None:
                invite = find_invite(list_tester, community_id, invite_id)
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
    def wrapper_get_role_ids(client: FlaskClient, community_id: int):
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
    def wrapper_get_roles_list(client, community_id: int, role_ids: list) -> list[dict]:
        """Check the success of getting the list of roles"""
        result = check_code(client.get(f"/communities/{community_id}/roles/"))
        roles = []
        for role in result:
            if role['id'] in role_ids:
                role.pop("permissions")
                roles.append(role)
        assert isinstance(roles, list)
        return roles
    return wrapper_get_roles_list
