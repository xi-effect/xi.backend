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
)

COMMUNITY_DATA: dict = {"name": "test"}
INVITATIONS_PER_REQUEST = 20


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


@fixture(scope="package")
def create_participant_role() -> Callable:
    def create_participant_role_wrapper(
        permission_type: PermissionType, community_id: int, client: FlaskClient
    ) -> int:
        response = client.get("/home/")
        user_id = check_code(response, get_json=True)["id"]
        role = Role.create(name="test_name", color="CD5C5C", community_id=community_id)
        RolePermission.create(role_id=role.id, permissions=[permission_type])
        participant = Participant.find_by_ids(
            community_id=community_id, user_id=user_id
        )
        assert participant is not None
        ParticipantRole.create(role_ids=[role.id], participant_id=participant.id)
        db.session.commit()
        return role.id

    return create_participant_role_wrapper


@fixture(scope="package")
def assert_successful_get() -> Callable:
    def assert_successful_get_wrapper(client: FlaskClient, code, joined: bool) -> None:
        data = check_code(client.get(f"/communities/join/{code}/"))
        assert data.get("joined") is joined
        assert data.get("authorized") is True

        community = data.get("community")
        assert community is not None
        assert dict_equal(community, COMMUNITY_DATA, *COMMUNITY_DATA.keys())

    return assert_successful_get_wrapper


@fixture(scope="package")
def create_assert_successful_join(assert_successful_get) -> Callable:
    def assert_successful_join_wrapper(list_tester, community_id):
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
