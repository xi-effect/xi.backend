from __future__ import annotations

from flask_fullstack import SocketIOTestClient, assert_contains

from communities.base import Community
from communities.base.roles_db import (
    LIMITING_QUANTITY_ROLES,
    PermissionType,
    Role,
    RolePermission,
)
from test.conftest import delete_by_id


def get_roles_list(client, community_id: int) -> list[dict]:
    """Check the success of getting the list of roles"""
    return client.get(f"/communities/{community_id}/roles/")


def test_roles(
    client,
    socketio_client,
    test_community,
):
    # Create second owner & base clients
    socketio_client2 = SocketIOTestClient(client)

    # Create valid & invalid permissions list
    permissions: list[str] = sorted(PermissionType.get_all_field_names())
    incorrect_permissions: list[str] = ["test"]

    role_data = {
        "permissions": permissions,
        "name": "test_role",
        "color": "FFFF00",
    }
    community_id_json = {"community_id": test_community}

    # Check successfully open roles-room
    for user in (socketio_client, socketio_client2):
        user.assert_emit_success("open_roles", community_id_json)

    # Assert limiting quantity creating roles in a community
    successful_role_data = {**role_data}
    role_data.update(community_id_json)

    for _ in range(LIMITING_QUANTITY_ROLES):
        socketio_client.assert_emit_ack(
            event_name="new_role",
            data=role_data,
            expected_data={
                **successful_role_data,
                "id": int,
            },
        )
        socketio_client2.assert_only_received("new_role", successful_role_data)

    socketio_client.assert_emit_success(
        event_name="new_role",
        data=role_data,
        code=400,
        message="Quantity exceeded",
    )

    # Delete 50 roles
    for index, role_data in enumerate(get_roles_list(client, test_community)):
        if index == 0:
            continue
        assert_contains(role_data, successful_role_data)
        data = {**community_id_json, "role_id": role_data["id"]}
        socketio_client.assert_emit_success("delete_role", data)
        socketio_client2.assert_only_received("delete_role", data)

    assert len(get_roles_list(client, test_community)) == 1

    # Assert role creation with different data

    second_role_data = {**role_data}
    second_role_data.pop("permissions")
    third_role_data = {**role_data}
    third_role_data.pop("color")
    incorrect_role_data = {**role_data, "permissions": incorrect_permissions}
    roles_data_list = [role_data, second_role_data, third_role_data]

    socketio_client.assert_emit_ack(
        "new_role",
        data={**incorrect_role_data, **community_id_json},
        expected_code=400,
        expected_message="Incorrect permissions",
    )

    for data in roles_data_list:
        role_id = socketio_client.assert_emit_ack(
            event_name="new_role",
            data={**data, **community_id_json},
            expected_data={**data, "id": int},
        )["id"]
        socketio_client2.assert_only_received("new_role", {**data, "id": role_id})

    assert (
        len(get_roles_list(client, community_id=test_community))
        == len(roles_data_list) + 1
    )

    # Assert role update with different data
    update_data = {
        "name": "update_test_name_role",
        "color": "00008B",
    }

    empty_role_data = {**community_id_json, "role_id": role_id}
    update_role_data = update_data | empty_role_data
    successful_data = {**update_data, "id": role_id}
    list_permissions = [permissions[1:], [], permissions]
    list_data = [update_role_data, successful_data]

    for data in list_permissions:
        for role_data in list_data:
            role_data["permissions"] = data
        socketio_client.assert_emit_ack(
            event_name="update_role",
            data=update_role_data,
            expected_data=successful_data,
        )
        socketio_client2.assert_only_received("update_role", successful_data)

    socketio_client.assert_emit_ack(
        event_name="update_role",
        data=empty_role_data,
        expected_data=successful_data,
    )
    socketio_client2.assert_only_received("update_role", successful_data)

    update_role_data["permissions"] = incorrect_permissions
    socketio_client.assert_emit_ack(
        event_name="update_role",
        data=update_role_data,
        expected_code=400,
        expected_message="Incorrect permissions",
    )

    # Check successfully close roles-room
    for user in (socketio_client, socketio_client2):
        user.assert_emit_success("close_roles", community_id_json)


def test_role_constraints(
    community_id: int,
):
    role_id = Role.create("test", "FFFF00", community_id).id
    RolePermission.create(role_id=role_id, permission_type=PermissionType.MANAGE_ROLES)
    assert Role.find_by_id(role_id) is not None
    assert len(RolePermission.get_all_by_role(role_id)) == 1

    delete_by_id(community_id, Community)
    assert Role.find_by_id(role_id) is None
    assert len(RolePermission.get_all_by_role(role_id)) == 0
