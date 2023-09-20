from __future__ import annotations

from typing import Any

import pytest
from flask_fullstack import SocketIOTestClient, dict_cut
from pydantic_marshals.contains import UnorderedLiteralCollection
from pytest_mock import MockerFixture

from communities.base import Community
from communities.base.roles_db import PermissionType, Role, RolePermission
from test.conftest import delete_by_id, FlaskTestClient


def create_role(
    socketio_client: SocketIOTestClient,
    community_id: int,
    role_data: dict[str, Any],
    role_watcher_client: SocketIOTestClient | None = None,
) -> int:
    expected: dict[str, Any] = {
        **role_data,
        "permissions": UnorderedLiteralCollection(set(role_data["permissions"])),
        "id": int,
    }
    role_id = socketio_client.assert_emit_ack(
        event_name="new_role",
        data={**role_data, "community_id": community_id},
        expected_data=expected,
    )["id"]
    if role_watcher_client is not None:
        role_watcher_client.assert_only_received("new_role", expected)
    return role_id


@pytest.fixture()
def role_watcher_client(
    client: FlaskTestClient,
    test_community: int,
) -> SocketIOTestClient:
    watcher_client = SocketIOTestClient(client)
    watcher_client.assert_emit_success("open_roles", {"community_id": test_community})
    yield watcher_client
    watcher_client.assert_emit_success("close_roles", {"community_id": test_community})


@pytest.fixture()
def role_data() -> dict[str, Any]:
    return {
        "name": "role",
        "color": "FFFF00",
        "permissions": list(sorted(PermissionType.get_all_field_names())),
    }


def test_create_role(
    client: FlaskTestClient,
    socketio_client: SocketIOTestClient,
    test_community: int,
    role_watcher_client: SocketIOTestClient,
    role_data: dict[str, Any],
) -> None:
    role_id = create_role(
        socketio_client, test_community, role_data, role_watcher_client
    )
    client.get(
        f"/communities/{test_community}/roles/",
        expected_json=[
            {
                **role_data,
                "permissions": UnorderedLiteralCollection(
                    set(role_data["permissions"])
                ),
                "id": role_id,
            }
        ],
    )
    delete_by_id(role_id, Role)


def test_roles_limit(
    mocker: MockerFixture,
    client: FlaskTestClient,
    socketio_client: SocketIOTestClient,
    test_community: int,
    role_watcher_client: SocketIOTestClient,
    role_data: dict[str, Any],
) -> None:
    mocker.patch.object(target=Role, attribute="max_count", new=0)

    socketio_client.assert_emit_success(
        event_name="new_role",
        data={**role_data, "community_id": test_community},
        code=400,
        message="Quantity exceeded",
    )
    role_watcher_client.assert_nop()
    client.get(f"/communities/{test_community}/roles/", expected_json=[])


@pytest.mark.parametrize(
    ("data", "code", "message"),
    [
        pytest.param(
            {"permissions": ["test"]},
            400,
            "Incorrect permissions",
            id="incorrect_permissions",
        ),
        # TODO add after new-marshals enable string checks
        #  ``pytest.param(({"color": "bad"}, 400, "Bad color"), id="bad_color"),``
        #  ``pytest.param(({"color": "00000000"}, 400, "Too long"), id="bad_color"),``
    ],
)
def test_role_validation(
    client: FlaskTestClient,
    socketio_client: SocketIOTestClient,
    test_community: int,
    role_watcher_client: SocketIOTestClient,
    role_data: dict[str, Any],
    data: dict[str, Any],
    code: int,
    message: str,
) -> None:
    socketio_client.assert_emit_success(
        event_name="new_role",
        data={**role_data, "community_id": test_community, **data},
        code=code,
        message=message,
    )
    role_watcher_client.assert_nop()
    client.get(f"/communities/{test_community}/roles/", expected_json=[])


@pytest.fixture()
def role(role_data: dict[str, Any], test_community: int) -> Role:
    role = Role.create(
        **dict_cut(role_data, "name", "color"),
        community_id=test_community,
    )
    RolePermission.create_bulk(
        role_id=role.id,
        permissions=[
            PermissionType.from_string(permission)
            for permission in role_data["permissions"]
        ],
    )
    yield role
    role.delete()


@pytest.fixture()
def role_ids(role: Role, test_community: int) -> dict[str, int]:
    return {"community_id": test_community, "role_id": role.id}


@pytest.mark.parametrize(
    "data",
    [
        pytest.param({"name": "update", "color": "00008B"}, id="name_and_color"),
        pytest.param({"permissions": []}, id="empty_permissions"),
        pytest.param({"permissions": ["manage-roles"]}, id="one_permission"),
    ],
)
def test_update_role(
    client: FlaskTestClient,
    socketio_client: SocketIOTestClient,
    test_community: int,
    role_watcher_client: SocketIOTestClient,
    role_data: dict[str, Any],
    role_ids: dict[str, int],
    data: dict[str, Any],
) -> None:
    expected_data: dict[str, Any] = {
        **role_data,
        **data,
        "permissions": UnorderedLiteralCollection(
            set(data.get("permissions", PermissionType.get_all_field_names()))
        ),
    }
    socketio_client.assert_emit_ack(
        event_name="update_role",
        data={**data, **role_ids},
        expected_data=expected_data,
    )
    role_watcher_client.assert_only_received(
        "update_role",
        {**expected_data, "id": role_ids["role_id"]},  # TODO add community_id?
    )
    client.get(f"/communities/{test_community}/roles/", expected_json=[expected_data])


def test_delete_role(
    client: FlaskTestClient,
    socketio_client: SocketIOTestClient,
    test_community: int,
    role_watcher_client: SocketIOTestClient,
    role: Role,
) -> None:
    role_ids = {"role_id": role.id, "community_id": test_community}
    socketio_client.assert_emit_ack(
        event_name="delete_role",
        data=role_ids,
    )
    role_watcher_client.assert_only_received("delete_role", role_ids)
    client.get(f"/communities/{test_community}/roles/", expected_json=[])


def test_role_constraints(community_id: int):
    role_id = Role.create("test", "FFFF00", community_id).id
    RolePermission.create(role_id=role_id, permission_type=PermissionType.MANAGE_ROLES)
    assert Role.find_by_id(role_id) is not None
    assert len(RolePermission.get_all_by_role(role_id)) == 1

    delete_by_id(community_id, Community)
    assert Role.find_by_id(role_id) is None
    assert len(RolePermission.get_all_by_role(role_id)) == 0
