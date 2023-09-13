from __future__ import annotations

from collections.abc import Callable

from flask_fullstack import SocketIOTestClient, dict_rekey, assert_contains
from pydantic import conlist
from pytest import mark

from common import User
from communities.base import Participant, Community, PermissionType
from test.communities.conftest import assert_create_community
from test.conftest import delete_by_id, FlaskTestClient
from test.vault_test import upload
from vault import File


def get_communities_list(client: FlaskTestClient) -> list[dict]:
    return client.get("/home/", expected_json={"communities": list})["communities"]


def get_participants_list(
    client: FlaskTestClient, community_id: int, username: str | None = None
) -> list[dict]:
    link = f"/communities/{community_id}/participants/"
    if username is not None:
        link += f"?search={username}"  # noqa: WPS336
    return list(client.paginate(link))


@mark.order(1000)
def test_meta_creation(client: FlaskTestClient, socketio_client: SocketIOTestClient):
    community_ids = [d["id"] for d in get_communities_list(client)]

    community_data = {"name": "12345", "description": "test"}
    community_id = assert_create_community(socketio_client, community_data)
    client.get(
        f"/communities/{community_id}/",
        expected_json={
            "id": int,
            "roles": [],
            "permissions": conlist(
                str,
                min_items=len(PermissionType.get_all_field_names()),
                max_items=len(PermissionType.get_all_field_names()),
            ),  # TODO upgrade list-via-set check
            "community": {"name": "12345", "description": "test"},
        },
    )
    community_id_json = {"community_id": community_id}
    community_ids.append(community_id)

    found = False
    for data in get_communities_list(client):
        assert data["id"] in community_ids
        if data["id"] == community_id:
            assert not found
            assert_contains(data, community_data)
            found = True
    assert found

    # Update metadata
    update_data = dict(**community_id_json, name="new_name", description="upd")
    for data in (update_data, dict(community_data, **community_id_json)):
        socketio_client.assert_emit_ack(
            event_name="update_community",
            data=data,
            expected_data=dict_rekey(data, community_id="id"),
        )

    # Set and delete avatar
    file_id = upload(client, "test-1.json")[0].get("id")
    assert File.find_by_id(file_id) is not None

    client.post(
        f"/communities/{community_id}/avatar/",
        json={"avatar-id": file_id},
        expected_a=True,
    )
    client.get(
        f"/communities/{community_id}/",
        expected_json={"community": {"avatar": {"id": file_id}}},
    )

    client.delete(f"/communities/{community_id}/avatar/", expected_a=True)
    client.get(f"/communities/{community_id}/", expected_json={"avatar": None})


@mark.order(1005)
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
            "permissions": conlist(
                str,
                min_items=len(PermissionType.get_all_field_names()),
                max_items=len(PermissionType.get_all_field_names()),
            ),  # TODO upgrade list-via-set check,
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

    participant_data.pop("role_ids")
    successful_participant_data.pop("roles")
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
