from __future__ import annotations

from flask_fullstack import dict_equal, check_code

from common.testing import SocketIOTestClient
from communities.base import RolePermission
from common import db

PERMISSIONS_LIST = ["create", "read", "update", "delete"]


def get_roles_list(client, community_id: int) -> list[dict]:
    """Check the success of getting the list of roles"""
    result = check_code(client.get(f"/communities/{community_id}/roles/"))
    assert isinstance(result, list)
    return result


def test_role_creation(
        client,
        socketio_client,
        test_community,
):
    # Create second owner & base clients
    socketio_client2 = SocketIOTestClient(client)

    community_id_json = {"community_id": test_community}

    # Check successfully open roles-room
    for user in (socketio_client, socketio_client2):
        user.assert_emit_success("open_roles", community_id_json)

    role_data = {
        "name": "test_role",
        "color": "black",
        "permissions": PERMISSIONS_LIST,
    }
    role_data.update(community_id_json)

    result_data = socketio_client.assert_emit_ack("new_role", role_data)
    role_data.pop("permissions")
    role_data.setdefault("id", 1)
    assert dict_equal(result_data, role_data, "name", "color", "id")
    socketio_client2.assert_only_received("new_role", result_data)

    # Check successfully close roles-room
    for user in (socketio_client, socketio_client2):
        user.assert_emit_success("close_roles", community_id_json)

    print(get_roles_list(client, test_community))
    print(db.session.execute(db.select(RolePermission)).scalars().all())
    print(PERMISSIONS_LIST)
    PERMISSIONS_LIST.pop(3)
    PERMISSIONS_LIST.pop(2)
    PERMISSIONS_LIST.pop(1)
    print(PERMISSIONS_LIST)
    role_data_for_update = {"name": "updated_test_role", "color": "green", "permissions": PERMISSIONS_LIST,
                            "community_id": test_community, "role_id": 1}

    result_data2 = socketio_client.assert_emit_ack("update_role", role_data_for_update)
    print(result_data2)
    print(result_data)
    print(db.session.execute(db.select(RolePermission)).scalars().all())
