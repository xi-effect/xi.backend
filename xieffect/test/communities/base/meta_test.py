from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from flask_fullstack import SocketIOTestClient, dict_rekey
from pydantic_marshals.contains import assert_contains, UnorderedLiteralCollection

from communities.base.meta_db import Participant, Community, PermissionType
from test.communities.conftest import assert_create_community
from test.conftest import delete_by_id, FlaskTestClient
from users.users_db import User
from vault.files_db import File


def get_communities_list(client: FlaskTestClient) -> list[dict]:
    return client.get("/home/", expected_json={"communities": list})["communities"]


def get_participants_list(
    client: FlaskTestClient, community_id: int, username: str | None = None
) -> list[dict]:
    link = f"/communities/{community_id}/participants/"
    if username is not None:
        link += f"?search={username}"  # noqa: WPS336
    return list(client.paginate(link))


def test_open_close_communities(
    socketio_client: SocketIOTestClient,
    test_community: int,
):
    socketio_client.assert_emit_success(
        event_name="open_communities", data={"community_id": test_community}
    )
    socketio_client.assert_emit_success(
        event_name="close_communities", data={"community_id": test_community}
    )


@pytest.mark.parametrize(
    "data",
    [
        pytest.param({"name": "update", "description": "update"}, id="full"),
        pytest.param({"name": "update"}, id="only_name"),
        pytest.param({"description": "update"}, id="only_description"),
    ],
)
def test_update_community(
    socketio_client: SocketIOTestClient,
    test_community: int,
    data: dict[str, Any],
):
    data["community_id"] = test_community
    socketio_client.assert_emit_ack(
        event_name="update_community",
        data=data,
        expected_data=dict_rekey(data, community_id="id"),
    )


def test_update_avatar(
    socketio_client: SocketIOTestClient,
    community: Community,
    file: File,
    file_maker: Callable[[str], File],
):
    check_data: dict[str, Any] = {
        "id": community.id,
        "name": community.name,
        "description": community.description,
    }

    # Setting an avatar
    socketio_client.assert_emit_ack(
        event_name="update_community",
        data={"community_id": community.id, "avatar_id": file.id},
        expected_data={
            **check_data,
            "avatar": {"id": file.id, "filename": file.filename},
        },
    )

    # Updating with a new avatar
    new_file: File = file_maker("test-2.json")
    socketio_client.assert_emit_ack(
        event_name="update_community",
        data={"community_id": community.id, "avatar_id": new_file.id},
        expected_data={
            **check_data,
            "avatar": {"id": new_file.id, "filename": new_file.filename},
        },
    )

    # Checking if old avatar was deleted
    assert File.find_by_id(file.id) is None


def test_delete_avatar(
    socketio_client: SocketIOTestClient,
    community: Community,
    file_id: int,
):
    community.avatar_id = file_id

    socketio_client.assert_emit_ack(
        event_name="update_community",
        data={"community_id": community.id, "avatar_id": None},
        expected_data={
            "id": community.id,
            "name": community.name,
            "description": community.description,
            "avatar": None,
        },
    )
    assert File.find_by_id(file_id) is None


def test_avatar_not_found(
    socketio_client: SocketIOTestClient,
    test_community: int,
    file_id: int,
):
    delete_by_id(file_id, File)
    socketio_client.assert_emit_ack(
        event_name="update_community",
        data={"community_id": test_community, "avatar_id": file_id},
        expected_code=404,
        expected_message=File.not_found_text,
    )


@pytest.mark.order(1000)
def test_meta_creation(client: FlaskTestClient, socketio_client: SocketIOTestClient):
    community_ids = [d["id"] for d in get_communities_list(client)]

    community_data = {"name": "12345", "description": "test"}
    community_id = assert_create_community(socketio_client, community_data)
    client.get(
        f"/communities/{community_id}/",
        expected_json={
            "id": int,
            "roles": [],
            "permissions": UnorderedLiteralCollection(
                PermissionType.get_all_field_names()
            ),
            "community": {"name": "12345", "description": "test"},
        },
    )
    community_ids.append(community_id)

    found = False
    for data in get_communities_list(client):
        assert data["id"] in community_ids
        if data["id"] == community_id:
            assert not found
            assert_contains(data, community_data)
            found = True
    assert found


@pytest.mark.order(1005)
def test_community_list(client: FlaskTestClient, socketio_client: SocketIOTestClient):
    def assert_order():
        for i, data in enumerate(get_communities_list(client)):
            assert data["id"] == community_ids[i]

    socketio_client2 = SocketIOTestClient(client)
    community_ids = [d["id"] for d in get_communities_list(client)]
    assert_order()

    # Creating
    def assert_double_create(data: dict):
        community_id = assert_create_community(socketio_client, data)
        socketio_client2.assert_received("new_community", dict(data, id=community_id))
        return community_id

    community_datas: list[dict[str, str | int]] = [
        {"name": "12345"},
        {"name": "54321", "description": "hi"},
        {"name": "test", "description": "i"},
    ]

    for community_data in community_datas:
        community_data["id"] = assert_double_create(community_data)
        community_ids.append(community_data["id"])

    user_id = client.get("/home/", expected_json={"id": int})["id"]
    real_ids = [community.id for community in Participant.get_communities_list(user_id)]
    assert len(real_ids) == len(community_ids)
    assert real_ids == community_ids

    # Reordering
    reorder_data = {
        "source_id": community_datas[0]["id"],
        "target_index": community_datas[-1]["id"],
    }
    socketio_client.assert_emit_success("reorder_community", reorder_data)
    socketio_client2.assert_only_received("reorder_community", reorder_data)

    community_ids.remove(reorder_data["source_id"])
    community_ids.insert(reorder_data["target_index"] - 1, reorder_data["source_id"])
    # assert_order

    # Leaving
    leave_data = {"community_id": community_datas[-1]["id"]}
    socketio_client.assert_emit_success("leave_community", leave_data)
    socketio_client2.assert_only_received("leave_community", leave_data)

    community_ids.remove(leave_data["community_id"])
    client.get(
        "/home/",
        expected_json={"communities": [{"id": value} for value in community_ids]},
    )


def test_community_delete(
    client: FlaskTestClient,
    socketio_client: SocketIOTestClient,
):
    community_id = assert_create_community(socketio_client, {"name": "test"})
    socketio_client.assert_emit_success(
        "delete_community", {"community_id": community_id}
    )
    client.get(
        f"/communities/{community_id}/",
        expected_status=404,
        expected_a="Community not found",
    )
    delete_by_id(community_id, Community)


def test_participant_constraints(
    table: type[User | Community],
    base_user_id: int,
    community_id: int,
):
    delete_by_id(base_user_id if (table == User) else community_id, table)
    assert Participant.find_by_ids(community_id, base_user_id) is None


def test_participant(
    client: FlaskTestClient,
    multi_client: Callable[str],
    socketio_client: SocketIOTestClient,
    test_community: int,
    get_role_ids: Callable[FlaskTestClient, int],
    get_roles_list_by_ids: Callable[FlaskTestClient, int, list[int]],
):
    socketio_client2 = SocketIOTestClient(client)
    community_id_json = {"community_id": test_community}

    # Check successfully open participants-room
    for user in (socketio_client, socketio_client2):
        user.assert_emit_success("open_participants", community_id_json)

    user = client.get(
        "/home/",
        expected_json={
            "username": str,
            "id": int,
        },
    )
    username, user_id = user.get("username"), user.get("id")
    assert len(participants_list := get_participants_list(client, test_community)) != 0
    assert len(get_participants_list(client, test_community, username)) != 0
    participant_id, community_id = participants_list[0].get("id"), participants_list[
        0
    ].get("community-id")

    role_ids = get_role_ids(client, test_community)

    # Participant update data
    participant_data = {
        "role_ids": role_ids,
        "participant_id": participant_id,
        **community_id_json,
    }
    roles = get_roles_list_by_ids(client, test_community, role_ids)
    successful_participant_data = {
        "community_id": community_id,
        "id": participant_id,
        "user_id": user_id,
        "roles": roles,
    }
    # Assert participant update with different data
    socketio_client.assert_emit_ack(
        "update_participant",
        participant_data,
        expected_data=successful_participant_data,
    )

    client.get(  # TODO use non-owner to test this
        f"/communities/{test_community}/",
        expected_json={
            "permissions": UnorderedLiteralCollection(
                PermissionType.get_all_field_names()
            ),
            "roles": roles,
        },
    )

    socketio_client2.assert_only_received(
        "update_participant", successful_participant_data
    )

    slice_role_ids = len(role_ids) // 2
    participant_data["role_ids"] = role_ids[slice_role_ids:]
    successful_participant_data["roles"] = get_roles_list_by_ids(
        client, test_community, role_ids[slice_role_ids:]
    )
    socketio_client.assert_emit_ack(
        "update_participant",
        participant_data,
        expected_data=successful_participant_data,
    )

    socketio_client2.assert_only_received(
        "update_participant", successful_participant_data
    )

    # delete participant data
    delete_data = {"community_id": test_community, "participant_id": participant_id}

    socketio_client.assert_emit_success(
        "delete_participant", delete_data, code=400, message="Target is the source"
    )

    client2 = multi_client("2@user.user")
    new_user_id = client2.get("/home/", expected_json={"id": int})["id"]
    new_participant_id = Participant.create(test_community, new_user_id).id

    delete_data["participant_id"] = new_participant_id

    socketio_client.assert_emit_success("delete_participant", delete_data)
    socketio_client2.assert_only_received("delete_participant", delete_data)

    for user in (socketio_client, socketio_client2):
        user.assert_emit_success("close_participants", community_id_json)
