from __future__ import annotations

from pytest import fixture
from collections.abc import Callable
from typing import Optional

from common.testing import SocketIOTestClient, dict_equal
from communities.base.roles_db import Role, RolePermission
from communities.base import Participant, Community, ParticipantRole, PermissionType
from common import db


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
def create_participant_roles():
    def wrapper(
        permission_type: PermissionType, community_id: int, add_permission: bool = False
    ) -> Optional[Callable]:
        role = Role.create(name="test_role", color="123456", community_id=community_id)
        RolePermission.create(role_id=role.id, permission_type=permission_type)
        db.session.add(
            ParticipantRole(role_id=role.id, participant_id=role.community_id)
        )
        db.session.commit()
        if add_permission:
            def inner(permission_type: PermissionType):
                RolePermission.create(role_id=role.id, permission_type=permission_type)

            return inner

    return wrapper


@fixture
def last_participant_id(socketio_client: SocketIOTestClient):
    def wrapper(create_community: bool = False):
        if create_community:
            community = Community(**COMMUNITY_DATA)
            db.session.add(community)
            db.session.commit()
        return db.session.get_first(
            db.select(Participant.id).order_by(Participant.id.desc())
        )

    return wrapper
