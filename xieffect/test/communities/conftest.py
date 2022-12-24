from __future__ import annotations

from pytest import fixture

from common.testing import SocketIOTestClient, dict_equal
from communities.base.roles_db import (
    Role,
    ParticipantRole,
    RolePermission
)
from communities.base import Participant, Community
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
    def wrapper(permission_type, community_id: int):
        role = Role.create(name="test_role", color="123456", community_id=community_id)
        RolePermission.create(role_id=role.id, permission_type=permission_type)
        db.session.add(ParticipantRole(role_id=role.id, participant_id=role.community_id))
        db.session.commit()

    return wrapper


@fixture
def last_participant_id(socketio_client: SocketIOTestClient):
    def wrapper(create_community: bool = False):
        if create_community:
            community = Community(**COMMUNITY_DATA)
            db.session.add(community)
            db.session.commit()
            print(f"community_id: {community.id}")
        return db.session.get_first(
            db.select(Participant.id).order_by(Participant.id.desc())
        )

    return wrapper


@fixture
def print_participant_communities():
    def wrapper():
        print("model Participant: ")
        for p in db.session.get_all(db.select(Participant)):
            print(f"id: {p.id}, community_id: {p.community_id}, user_id: {p.user_id}")
        print("model Community: ")
        for c in db.session.get_all(db.select(Community)):
            print(f"id: {c.id}, name: {c.name}")

    return wrapper
