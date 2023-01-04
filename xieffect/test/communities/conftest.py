from __future__ import annotations

from collections.abc import Callable

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


def assert_create_community(
    socketio_client: SocketIOTestClient, community_data: dict
) -> int:
    result_data = socketio_client.assert_emit_ack("new_community", community_data)
    assert isinstance(result_data, dict)
    assert dict_equal(result_data, community_data, *community_data.keys())

    community_id = result_data.get("id")
    assert isinstance(community_id, int)
    return community_id


@fixture
def test_community(socketio_client: SocketIOTestClient) -> int:
    # TODO use yield & delete the community after
    return assert_create_community(socketio_client, COMMUNITY_DATA)


@fixture
def create_participant_role() -> Callable:
    def create_participant_role_wrapper(
        permission_type: PermissionType, community_id: int
    ) -> int:
        role = Role.create(name="test_name", color="CD5C5C", community_id=community_id)
        RolePermission.create(role_id=role.id, permission_type=permission_type)
        participant_id = db.session.get_first(
            db.select(Participant.id).order_by(Participant.id.desc())
        )
        if permission_type == "MANAGE_NEWS":
            participant_id -= 1
        db.session.add(ParticipantRole(role_id=role.id, participant_id=participant_id))
        db.session.commit()
        return role.id

    return create_participant_role_wrapper


@fixture
def create_permission() -> Callable:
    def create_permission_wrapper(
        permission_type: PermissionType, role_id: int
    ) -> None:
        RolePermission.create(role_id=role_id, permission_type=permission_type)

    return create_permission_wrapper
