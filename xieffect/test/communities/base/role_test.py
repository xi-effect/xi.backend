from __future__ import annotations

from flask_fullstack import dict_equal, check_code

from common.testing import SocketIOTestClient
from communities.base.role_db import LIMITING_QUANTITY_ROLES

PERMISSIONS_LIST = ["create", "delete", "read", "update"]


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

    community_id_json = {"community_id": test_community}

    role_data = {
        "name": "test_role",
        "color": "FFFF00",
        "permissions": PERMISSIONS_LIST,
    }
    role_data.update(community_id_json)

    second_role_data = role_data.copy()

    second_role_data.pop("permissions")

    # Check successfully open roles-room
    for user in (socketio_client, socketio_client2):
        user.assert_emit_success("open_roles", community_id_json)

    # Assert limiting quantity creating roles in a community
    for i in range(1, LIMITING_QUANTITY_ROLES + 2):

        if i == LIMITING_QUANTITY_ROLES + 1:
            assert (
                socketio_client.assert_emit_ack(
                    event_name="new_role",
                    data=role_data,
                    code=400,
                    message="Quantity exceeded",
                )
                is None
            )
        else:
            result_data = socketio_client.assert_emit_ack("new_role", role_data)
            socketio_client2.assert_only_received("new_role", result_data)

    role_data_for_delete = dict(
        name="test_role", color="FFFF00", permission=PERMISSIONS_LIST
    )

    # Assert 50 roles
    for index, data in enumerate(get_roles_list(client, test_community), 1):
        role_data_for_delete["id"] = index
        assert dict_equal(data, role_data_for_delete)

    # Delete 50 roles
    for pk in range(1, LIMITING_QUANTITY_ROLES + 1):
        data = dict(community_id_json, role_id=pk)
        socketio_client.assert_emit_success("delete_role", data)
        socketio_client2.assert_only_received("delete_role", data)

    assert len(get_roles_list(client, test_community)) == 0

    # Assert role creation with different data
    third_role_data = role_data.copy()
    third_role_data.pop("color")
    fourth_role_data = role_data.copy()
    fourth_role_data["permissions"] = ["test1", "test2"]
    roles_data_list = [role_data, second_role_data, third_role_data, fourth_role_data]

    global role_id

    for index, data in enumerate(roles_data_list, 1):
        print(index, data)
        if index == len(roles_data_list):
            socketio_client.assert_emit_ack(
                "new_role", data, code=400, message="Permissions aren't correct"
            )
        else:
            result_data = socketio_client.assert_emit_ack("new_role", data)
            socketio_client2.assert_only_received("new_role", result_data)
            role_id = result_data.get("id")
            assert isinstance(role_id, int)
            data.pop("community_id")
            assert dict_equal(result_data, data, *data.keys())

    assert (
        len(get_roles_list(client, community_id=test_community))
        == len(roles_data_list) - 1
    )

    data_for_update_role = {
        "role_id": role_id,
        "name": "update_test_name_role",
        "color": "00008B",
        "permissions": PERMISSIONS_LIST[1:3],
        "community_id": test_community,
    }

    # Assert update role
    for index in range(2):
        if index == 2:
            data_for_update_role["permissions"] = ["something", "anything"]
            socketio_client.assert_emit_ack(
                "update_role",
                data_for_update_role,
                code=400,
                message="Permissions aren't correct",
            )
        else:
            # Check correct update role
            successful_data = {
                "permissions": ["delete", "read"],
                "name": "update_test_name_role",
                "color": "00008B",
                "id": role_id,
            }

            result_data = socketio_client.assert_emit_ack(
                "update_role", data_for_update_role
            )
            socketio_client2.assert_only_received("update_role", result_data)

            assert dict_equal(
                result_data, successful_data, "permissions", "name", "color", "id"
            )

    # Check successfully close roles-room
    for user in (socketio_client, socketio_client2):
        user.assert_emit_success("close_roles", community_id_json)
