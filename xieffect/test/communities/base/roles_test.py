from __future__ import annotations

from flask_fullstack import SocketIOTestClient, assert_contains, dict_reduce

from communities.base import Community
from communities.base.roles_db import (
    LIMITING_QUANTITY_ROLES,
    PermissionType,
    Role,
    RolePermission,
)
from test.conftest import delete_by_id, FlaskTestClient


def get_roles_list(client: FlaskTestClient, community_id: int) -> list[dict]:
    """Check the success of getting the list of roles"""
    return client.get(f"/communities/{community_id}/roles/", expected_json=list)


def test_roles(
    client: FlaskTestClient,
    socketio_client: SocketIOTestClient,
    test_community: int,
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
    successful_role_data = dict(**role_data)
    role_data.update(community_id_json)

    for _ in range(LIMITING_QUANTITY_ROLES):
        socketio_client.assert_emit_ack(
            event_name="new_role",
            data=role_data,
            expected_data=dict(successful_role_data, id=int),
        )
        socketio_client2.assert_only_received("new_role", successful_role_data)

    socketio_client.assert_emit_success(
        event_name="new_role",
        data=role_data,
        code=400,
        message="Quantity exceeded",
    )

    # Delete 50 roles
    for data in get_roles_list(client, test_community):
        assert_contains(data, successful_role_data)
        data = dict(community_id_json, role_id=data["id"])
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
        event_name="new_role",
        data=incorrect_role_data,
        expected_code=400,
        expected_message="Incorrect permissions",
    )

    for data in roles_data_list:
        expected_data = {
            **dict_reduce(data, "community_id"),
            "id": int,
        }
        role_id: int = socketio_client.assert_emit_ack(
            event_name="new_role",
            data=data,
            expected_data=expected_data,
        )["id"]
        socketio_client2.assert_only_received("new_role", expected_data)

    assert len(get_roles_list(client, community_id=test_community)) == len(
        roles_data_list
    )

    # Assert role update with different data
    update_data = {
        "name": "update_test_name_role",
        "color": "00008B",
        "permissions": permissions[1:],
    }

    update_role_data = dict(**update_data, **community_id_json, role_id=role_id)
    successful_data = dict(**update_data, id=role_id)
    second_update_role_data = update_role_data.copy()
    second_update_role_data.pop("name")
    second_update_role_data.pop("permissions")
    second_update_role_data.pop("color")
    update_data_list = [update_role_data, second_update_role_data]

    for data in update_data_list:
        socketio_client.assert_emit_ack(
            event_name="update_role",
            data=data,
            expected_data=successful_data,
        )
        socketio_client2.assert_only_received("update_role", successful_data)

    third_update_role_data = update_role_data.copy()
    third_update_role_data["permissions"] = []
    successful_data["permissions"] = []
    socketio_client.assert_emit_ack(
        event_name="update_role",
        data=third_update_role_data,
        expected_data=successful_data,
    )
    socketio_client2.assert_only_received("update_role", successful_data)

    four_update_role_data = update_role_data.copy()
    four_update_role_data["permissions"] = permissions
    successful_data.pop("permissions")
    real_permissions = socketio_client.assert_emit_ack(
        event_name="update_role",
        data=four_update_role_data,
        expected_data={"permissions": list, **successful_data},
    )["permissions"]
    assert set(real_permissions) == set(permissions)
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
    RolePermission.create(role_id, PermissionType.MANAGE_ROLES)
    assert Role.find_by_id(role_id) is not None
    assert len(RolePermission.get_all_by_role(role_id)) == 1

    delete_by_id(community_id, Community)
    assert Role.find_by_id(role_id) is None
    assert len(RolePermission.get_all_by_role(role_id)) == 0
