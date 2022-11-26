from __future__ import annotations

from pytest import fixture

from common.testing import SocketIOTestClient
from .base.meta_test import assert_create_community

COMMUNITY_DATA = {"name": "test"}


@fixture
def test_community(socketio_client: SocketIOTestClient) -> int:
    # TODO place more globally (duplicate from invites_test)
    # TODO use yield & delete the community after
    return assert_create_community(socketio_client, COMMUNITY_DATA)
