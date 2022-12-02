from __future__ import annotations

from flask_fullstack import dict_equal, check_code

from common import db
from common.testing import SocketIOTestClient
from communities.base.role_db import LimitingQuantityRoles, RolePermission, Role

PERMISSIONS_LIST = ['create', 'delete', 'read', 'update']


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

    role_data = {
        "name": "test_role",
        "color": "black",
        "permissions": PERMISSIONS_LIST,
    }
    role_data.update(community_id_json)

    second_role_data = role_data.copy()

    second_role_data.pop("permissions")

    # Check successfully open roles-room
    for user in (socketio_client, socketio_client2):
        user.assert_emit_success("open_roles", community_id_json)

    # Assert limiting quantity creating roles in a community
    for i in range(0, LimitingQuantityRoles + 2):

        if i == 50:
            assert (
                socketio_client.assert_emit_ack(
                    event_name="new_role",
                    data=role_data,
                    code=400,
                    message="quantity exceeded",
                )
                is None
            )

        else:
            result_data = socketio_client.assert_emit_ack("new_role", role_data)
            socketio_client2.assert_only_received("new_role", result_data)


    # Assert 50 roles
    for index, data in enumerate(get_roles_list(client, test_community), 1):
        assert data['name'] == "test_role"
        assert data["color"] == "black"
        assert data["id"] == index
        assert data["permissions"] == PERMISSIONS_LIST

    # Delete 50 roles
    for pk in range(1, LimitingQuantityRoles + 2):
        data = {"role_id": pk}
        data.update(community_id_json)
        socketio_client.assert_emit_success("delete_role", data)

    # assert (get_roles_list(client, test_community)) == []

    # # Assert role creation
    # result_data = socketio_client.assert_emit_ack("new_role", role_data)
    #
    # socketio_client2.assert_only_received("new_role", result_data)
    #
    # result2 = socketio_client.assert_emit_ack("new_role", second_role_data)
    #
    # socketio_client2.assert_only_received("new_role", result2)

    # role_id = result_data.get("id")
    # assert isinstance(role_id, int)
    # data_successfully_create = role_data.copy()
    # data_successfully_create.pop("permissions")
    # data_successfully_create.setdefault("id", role_id)
    # assert dict_equal(result_data, data_successfully_create, "name", "color", "id")

    # # Check successfully role creation
    # for data in get_roles_list(client, test_community):
    #     assert data.get("id") == role_id
    #     assert dict_equal(data, data_successfully_create, "name", "color", "id")
    #     role = Role.find_by_id(data.get("id"))
    #     assert role.id == data.get("id")
    #     assert role.name == data.get("name") == role_data.get("name")
    #     assert role.color == data.get("color") == role_data.get("color")
    #
    # list_role_permission = RolePermission.find_by_role(role_id)
    # assert len(list_role_permission) == 4
    #
    # role_dict_list = [
    #     {"name": "update_name", "color": "green", "role_id": role_id},
    # ]
    #
    # print(role_dict_list)
    #
    # # Assert role_update
    # # result_data = socketio_client.assert_emit_ack("update_role", {})
    #
    # # Check successfully close roles-room
    # for user in (socketio_client, socketio_client2):
    #     user.assert_emit_success("close_roles", community_id_json)


# print(db.session.execute(db.select(RolePermission)).scalars().all())
# PERMISSIONS_LIST.pop(3)
# PERMISSIONS_LIST.pop(2)
# PERMISSIONS_LIST.pop(1)
# role_data_for_update = {"name": "updated_test_role", "color": "green", "permissions": PERMISSIONS_LIST,
#                         "community_id": test_community, "role_id": 1}
#
# # check successfully update_role
# result_data2 = socketio_client.assert_emit_ack("update_role", role_data_for_update)
# print(result_data2)
# print(result_data)
# print(db.session.execute(db.select(RolePermission)).scalars().all())
# socketio_client.assert_emit_ack("delete_role", {"role_id": 1, "community_id": test_community})
#
# # Check successfully post delete
# pass
#
