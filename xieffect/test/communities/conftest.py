from __future__ import annotations

from pytest import fixture

from common import User
from common.testing import SocketIOTestClient, dict_equal
from communities.base import Community, Participant
from test.conftest import delete_by_id

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
def community_id(base_user_id) -> int:
    community_id = Community.create(
        name="test_community",
        description="description",
        creator=User.find_by_id(base_user_id),
    ).id
    assert Participant.find_by_ids(community_id, base_user_id) is not None
    yield community_id
    delete_by_id(community_id, Community)


@fixture(params=[User, Community])
def table(request) -> type[User | Community]:
    return request.param
