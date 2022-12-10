from __future__ import annotations

from flask_fullstack import dict_equal, check_code

from common.testing import SocketIOTestClient
from communities.base.roles_db import LIMITING_QUANTITY_ROLES, PermissionTypes


def get_roles_list(client, community_id: int) -> list[dict]:
    """Check the success of getting the list of roles"""
    result = check_code(client.get(f"/communities/{community_id}/roles/"))
    assert isinstance(result, list)
    return result


def test_roles(
    client,
    socketio_client,
    test_community,
):
    # Create second owner & base clients
    socketio_client2 = SocketIOTestClient(client)

    # Create valid & invalid permissions list
    permissions_list: list = [p.to_string() for p in PermissionTypes]
    incorrect_permissions: list = ["test"]

    role_data = {
        "permissions": sorted(permissions_list),
        "name": "test_role",
        "color": "FFFF00",
    }
    community_id_json = {"community_id": test_community}

    # Check successfully open roles-room
    for user in (socketio_client, socketio_client2):
        user.assert_emit_success("open_roles", community_id_json)

    # Assert limiting quantity creating roles in a community
    successful_role_data = dict(**role_data)
    role_data.update(community_id_json)

    for i in range(1, LIMITING_QUANTITY_ROLES + 2):
        if i == LIMITING_QUANTITY_ROLES + 1:
            socketio_client.assert_emit_success(
                event_name="new_role",
                data=role_data,
                code=400,
                message="Quantity exceeded",
            )
        else:
            successful_role_data["id"] = i
            result_data = socketio_client.assert_emit_ack("new_role", role_data)
            assert dict_equal(result_data, successful_role_data, *result_data.keys())
            socketio_client2.assert_only_received("new_role", successful_role_data)

    # Assert 50 roles
    for index, data in enumerate(get_roles_list(client, test_community), 1):
        successful_role_data["id"] = index
        assert dict_equal(data, successful_role_data)

    # Delete 50 roles
    for pk in range(1, LIMITING_QUANTITY_ROLES + 1):
        data = dict(community_id_json, role_id=pk)
        socketio_client.assert_emit_success("delete_role", data)
        socketio_client2.assert_only_received("delete_role", data)

    assert len(get_roles_list(client, test_community)) == 0

    # Assert role creation with different data
    second_role_data = role_data.copy()
    second_role_data.pop("permissions")
    third_role_data = role_data.copy()
    third_role_data.pop("color")
    incorrect_role_data = role_data.copy()
    incorrect_role_data["permissions"] = incorrect_permissions
    roles_data_list = [role_data, second_role_data, third_role_data]

    socketio_client.assert_emit_ack(
        "new_role", incorrect_role_data, code=400, message="Incorrect permissions"
    )

    for index, data in enumerate(roles_data_list, start=1):
        result_data = socketio_client.assert_emit_ack("new_role", data)
        data["id"] = index
        data.pop("community_id")
        assert dict_equal(data, result_data, *data.keys())
        socketio_client2.assert_only_received("new_role", data)
        role_id = result_data.get("id")
        assert isinstance(role_id, int)

    assert len(get_roles_list(client, community_id=test_community)) == len(
        roles_data_list
    )

    update_data = {
        "name": "update_test_name_role",
        "color": "00008B",
        "permissions": sorted(permissions_list[1:]),
    }

    data_for_update_role = dict(**update_data, **community_id_json, role_id=role_id)

    successful_data_for_update_role = dict(**update_data, id=role_id)

    # Assert update role
    result_data = socketio_client.assert_emit_ack("update_role", data_for_update_role)
    assert dict_equal(
        result_data,
        successful_data_for_update_role,
        *successful_data_for_update_role.keys(),
    )
    socketio_client2.assert_only_received(
        "update_role", successful_data_for_update_role
    )

    data_for_update_role["permissions"] = incorrect_permissions
    socketio_client.assert_emit_ack(
        "update_role",
        data_for_update_role,
        code=400,
        message="Incorrect permissions",
    )

    # Check successfully close roles-room
    for user in (socketio_client, socketio_client2):
        user.assert_emit_success("close_roles", community_id_json)
