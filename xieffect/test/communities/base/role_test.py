from __future__ import annotations

from flask_fullstack import dict_equal, check_code
from pytest import mark

from common.testing import SocketIOTestClient

PERMISSIONS_LIST = ["create", "read", "update", "delete"]


@mark.order(1500)
def test_role_creation(
    client,
    multi_client,
    list_tester,
    socketio_client,
    test_community,
):
    # Create second owner & base clients
    socketio_client2 = SocketIOTestClient(client)

    community_id_json = {"community_id": test_community}

    # Check successfully open roles-room
    for user in (socketio_client, socketio_client2):
        user.assert_emit_success("open_roles", community_id_json)

    role_data = dict(
        community_id_json,
        name="test_role",
        color="black",
        permissions=PERMISSIONS_LIST
    )

    result_data = socketio_client.assert_emit_ack("new_role", role_data)
    role_data.pop('permissions')
    role_data.setdefault('id', 1)
    assert dict_equal(result_data, role_data, "name", "color", "community_id", "id")
    socketio_client2.assert_only_received("new_role", result_data)

    # Check successfully close roles-room
    for user in (socketio_client, socketio_client2):
        user.assert_emit_success("close_roles", community_id_json)
