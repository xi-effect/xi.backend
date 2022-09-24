from __future__ import annotations

from flask.testing import FlaskClient
from pytest import mark

from __lib__.flask_fullstack import check_code, dict_equal
from common.testing import SocketIOTestClient


def assert_create_community(socketio_client: SocketIOTestClient, community_data: dict) -> int:
    result_data = socketio_client.assert_emit_ack("new-community", community_data)
    assert isinstance(result_data, dict)
    assert dict_equal(result_data, community_data, *community_data.keys())

    community_id = result_data.get("id", None)
    assert isinstance(community_id, int)
    return community_id


def get_communities_list(client: FlaskClient) -> list[dict]:
    result = check_code(client.get("/home/")).get("communities", None)
    assert isinstance(result, list)
    return result


@mark.order(1000)
def test_meta_creation(client: FlaskClient, socketio_client: SocketIOTestClient):
    community_ids = [d["id"] for d in get_communities_list(client)]

    community_data = {"name": "12345", "description": "test"}
    community_id = assert_create_community(socketio_client, community_data)
    community_ids.append(community_id)

    found = False
    for data in get_communities_list(client):
        assert data["id"] in community_ids
        if data["id"] == community_id:
            assert not found
            assert dict_equal(data, community_data, *community_data.keys())
            found = True
    assert found


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
    def assert_double_create(community_data: dict):
        community_id = assert_create_community(socketio_client, community_data)
        socketio_client2.assert_received("new-community", dict(community_data, id=community_id))
        return community_id

    community_datas: list[dict[str, str | int]] = [
        {"name": "12345"},
        {"name": "54321", "description": "hi"},
        {"name": "test", "description": "i"},
    ]

    for community_data in community_datas:
        community_data["id"] = assert_double_create(community_data)
        community_ids.insert(0, community_data["id"])
    # assert_order

    # Reordering
    reorder_data = {"source-id": community_datas[0]["id"], "target-index": 0}
    socketio_client.assert_emit_ack("reorder-community", reorder_data, message="Success")
    socketio_client2.assert_only_received("reorder-community", reorder_data)

    community_ids.remove(reorder_data["source-id"])
    community_ids.insert(reorder_data["target-index"], reorder_data["source-id"])
    # assert_order

    # Leaving
    leave_data = {"community-id": community_datas[-1]["id"]}
    socketio_client.assert_emit_ack("leave-community", leave_data, message="Success")
    socketio_client2.assert_only_received("leave-community", leave_data)

    community_ids.remove(leave_data["community-id"])
    # assert_order
