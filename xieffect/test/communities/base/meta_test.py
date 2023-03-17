from __future__ import annotations

from flask.testing import FlaskClient
from flask_fullstack import check_code, dict_equal
from pytest import mark

from common import User
from common.testing import SocketIOTestClient
from communities.base import Participant, Community
from test.communities.conftest import assert_create_community
from test.conftest import delete_by_id
from test.vault_test import upload
from vault import File


def get_communities_list(client: FlaskClient) -> list[dict]:
    result = check_code(client.get("/home/")).get("communities")
    assert isinstance(result, list)
    return result


@mark.order(1000)
def test_meta_creation(client: FlaskClient, socketio_client: SocketIOTestClient):
    community_ids = [d["id"] for d in get_communities_list(client)]

    community_data = {"name": "12345", "description": "test"}
    community_id = assert_create_community(socketio_client, community_data)
    community_id_json = {"community_id": community_id}
    community_ids.append(community_id)

    found = False
    for data in get_communities_list(client):
        assert data["id"] in community_ids
        if data["id"] == community_id:
            assert not found
            assert dict_equal(data, community_data, *community_data.keys())
            found = True
    assert found

    # Update metadata
    update_data = dict(**community_id_json, name="new_name", description="upd")
    for data in (update_data, dict(community_data, **community_id_json)):
        new_meta = socketio_client.assert_emit_ack("update_community", data)
        dict_equal(new_meta, data, *data.keys())

    # Set and delete avatar
    file_id = upload(client, "test-1.json")[0].get("id")
    assert File.find_by_id(file_id) is not None

    url = f"/communities/{community_id}/"
    check_code(client.post(f"{url}avatar/", json={"avatar-id": file_id}))
    community_avatar = check_code(client.get(url)).get("avatar")
    assert community_avatar is not None
    assert community_avatar.get("id") == file_id

    check_code(client.delete(f"{url}avatar/"))
    assert check_code(client.get(url)).get("avatar") is None


@mark.order(1005)
def test_community_list(client: FlaskClient, socketio_client: SocketIOTestClient):
    def assert_order():
        for i, data in enumerate(get_communities_list(client)):
            assert data["id"] == community_ids[i]

    socketio_client2 = SocketIOTestClient(client)
    community_ids = [d["id"] for d in get_communities_list(client)]
    assert_order()

    # TODO check order with new community listing

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
        community_ids.insert(0, community_data["id"])

    user_id = check_code(client.get("/home/")).get("id")
    community_list = Participant.get_communities_list(user_id)
    check_list = [value == community_list[num].id for num, value in enumerate(community_ids[::-1])]
    assert all(check_list)
    # assert_order

    # Reordering
    reorder_data = {"source_id": community_datas[0]["id"], "target_index": 0}
    socketio_client.assert_emit_success("reorder_community", reorder_data)
    socketio_client2.assert_only_received("reorder_community", reorder_data)

    community_ids.remove(reorder_data["source_id"])
    community_ids.insert(reorder_data["target_index"], reorder_data["source_id"])
    # assert_order

    # Leaving
    leave_data = {"community_id": community_datas[-1]["id"]}
    socketio_client.assert_emit_success("leave_community", leave_data)
    socketio_client2.assert_only_received("leave_community", leave_data)

    community_ids.remove(leave_data["community_id"])
    community_list = check_code(client.get("/home/")).get("communities")
    check_list = [value == community_list[num].get("id") for num, value in enumerate(community_ids[::-1])]
    assert all(check_list)
    # assert_order


def test_community_delete(
    client: FlaskClient,
    socketio_client: SocketIOTestClient,
):
    community_id = assert_create_community(socketio_client, {"name": "test"})
    socketio_client.assert_emit_success("delete_community", {"community_id": community_id})
    assert check_code(client.get(f"/communities/{community_id}/"), 404).get("a") == "Community not found"

    delete_by_id(community_id, Community)


def test_participant_constraints(
    table: type[User | Community],
    base_user_id: int,
    community_id: int,
):
    delete_by_id(base_user_id if (table == User) else community_id, table)
    assert Participant.find_by_ids(community_id, base_user_id) is None
