from __future__ import annotations

from flask_socketio import SocketIOTestClient
from flask.testing import FlaskClient
from pytest import mark

from __lib__.flask_fullstack import dict_equal, check_code

from communities.services.channels_db import ChannelCategory


@mark.order(2000)
def test_post_creation(client: FlaskClient, socketio_client: SocketIOTestClient):
    community_ids = [d["id"] for d in get_communities_list(client)]

    community_data = {"name": "12345", "description": "test"}
    community_id = assert_create_community(socketio_client, community_data)
    community_ids.append(community_id)

    found_community = False
    for data in get_communities_list(client):
        assert data["id"] in community_ids
        if data["id"] == community_id:
            assert not found_community
            assert dict_equal(data, community_data, "name", "description")
            found_community = True
    assert found_community

    community_id_json = {"community_id": community_id}
    assert_open_categories(socketio_client, community_id_json)

    categories_ids = [d["id"] for d in get_categories_list(client, community_id)]
    categories_data = {
        "name": "cat",
        "description": "desc",
        "community_id": community_id,
        "next_id": 1
    }
    categories_id = assert_create_categories(socketio_client, categories_data)
    categories_ids.append(categories_id)

    found_categories = False
    for data in get_categories_list(client, community_id):
        assert data["id"] in categories_ids
        if data["id"] == categories_id:
            assert not found_categories
            assert dict_equal(data, categories_data, "name", "description")
            found_categories = True
    assert found_categories

    a = [None, 1, 2, 2, None, 1, None, 5, 4, None]
    for i in a:
        categories_data = {
            "name": f"cat{i}",
            "description": "desc",
            "community_id": community_id,
            "next_id": i
        }
        categories_id = assert_create_categories(socketio_client, categories_data)
        categories_ids.append(categories_id)

    assert ChannelCategory.find_by_id(1).prev_category_id == 7
    assert get_categories_list(client,community_id)[2]["id"] == 1
    assert ChannelCategory.find_by_id(4).next_category_id == 9
    assert get_categories_list(client, community_id)[6]["id"] == 5
    assert ChannelCategory.find_by_id(6).prev_category_id == 2
    assert ChannelCategory.find_by_id(8).next_category_id == 11
    assert get_categories_list(client, community_id)[9]["id"] == 8
    assert ChannelCategory.find_by_id(10).prev_category_id == 1

    category_update = {"community_id": community_id, "category_id": 1}
    assert_update_category(socketio_client, category_update, client)

    category_update1 = category_update.copy()
    category_update1["name"] = "new_name"
    assert_update_category(socketio_client, category_update1, client)
    category_update1["description"] = "new_description"
    assert_update_category(socketio_client, category_update1, client)

    category_update2 = category_update.copy()
    category_update2["description"] = "new_description2"
    assert_update_category(socketio_client, category_update2, client)

    category_move = {"community_id": community_id, "category_id": 2, "next_id": 4}
    assert_move_category(socketio_client, category_move)
    assert ChannelCategory.find_by_id(2).prev_category_id == 10
    assert ChannelCategory.find_by_id(10).next_category_id == 2
    assert ChannelCategory.find_by_id(5).next_category_id == 6
    assert ChannelCategory.find_by_id(6).prev_category_id == 5

    category_move = {"community_id": community_id, "category_id": 9}
    assert_move_category(socketio_client, category_move)
    assert ChannelCategory.find_by_id(9).prev_category_id == 11
    assert ChannelCategory.find_by_id(11).next_category_id == 9
    assert ChannelCategory.find_by_id(4).next_category_id == 5
    assert ChannelCategory.find_by_id(5).prev_category_id == 4

    assert_close_categories(socketio_client, community_id_json)

    ack = socketio_client.emit("leave-community", community_id_json, callback=True)
    assert dict_equal(ack, {"code": 200, "message": "Success"}, ("code", "message"))
    assert len(socketio_client.get_received()) == 0


def assert_create_community(
    socketio_client: SocketIOTestClient, community_data: dict
):
    ack = socketio_client.emit("new-community", community_data, callback=True)
    events = socketio_client.get_received()
    assert len(events) == 0
    assert ack.get("code") == 200

    result_data = ack.get("data")
    assert result_data is not None

    community_id = result_data.get("id")
    assert isinstance(community_id, int)
    assert dict_equal(result_data, community_data, *community_data.keys())
    return community_id


def assert_create_categories(socketio_client: SocketIOTestClient, category_data: dict):
    ack = socketio_client.emit("new-category", category_data, callback=True)
    events = socketio_client.get_received()
    assert len(events) == 0
    assert ack.get("code") == 200

    result_data = ack.get("data")
    assert result_data is not None

    category_id = result_data.get("id")
    assert isinstance(category_id, int)
    assert dict_equal(result_data, category_data, "name", "description")

    return category_id


def assert_update_category(
    socketio_client: SocketIOTestClient,
    category_upd: dict,
    client
):
    ack = socketio_client.emit("update-category", category_upd, callback=True)
    events = socketio_client.get_received()
    old_date = get_categories_list(client, category_upd["community_id"])[2]
    assert len(events) == 0
    assert ack.get("code") == 200

    result_data = ack.get("data")
    assert result_data is not None
    assert result_data["id"] == category_upd["category_id"]

    if category_upd.get("name") is None:
        assert result_data["name"] == old_date["name"]
    else:
        assert result_data["name"] == category_upd["name"]

    if category_upd.get("description") is None:
        if old_date.get("description") is not None:
            assert result_data["description"] == old_date["description"]
        else:
            assert result_data.get("description") is None
    else:
        assert result_data["description"] == category_upd["description"]


def assert_move_category(
    socketio_client: SocketIOTestClient,
    category_move: dict,
):
    ack = socketio_client.emit("move-category", category_move, callback=True)
    events = socketio_client.get_received()
    assert len(events) == 0
    assert ack.get("code") == 200

    result_data = ack.get("data")
    assert result_data is not None
    res_id = result_data.get("id")
    next_id = category_move.get("next_id")
    assert res_id == category_move["category_id"]
    assert ChannelCategory.find_by_id(res_id).next_category_id == next_id

    if next_id is not None:
        assert ChannelCategory.find_by_id(next_id).prev_category_id == res_id


def get_communities_list(client: FlaskClient):
    result = check_code(client.get("/home/")).get("communities", None)
    assert isinstance(result, list)
    return result


def get_categories_list(client: FlaskClient, community_id):
    result = check_code(
        client.get(f"/communities/{community_id}/")
    ).get("categories")
    assert isinstance(result, list)
    return result


def assert_open_categories(socketio_client: SocketIOTestClient, community_id: dict):
    ack = socketio_client.emit("open-category", community_id, callback=True)
    events = socketio_client.get_received()
    assert len(events) == 0
    assert ack.get("code") == 200
    assert ack.get("message") == "Success"


def assert_close_categories(socketio_client: SocketIOTestClient, community_id: dict):
    ack = socketio_client.emit("close-category", community_id, callback=True)
    events = socketio_client.get_received()
    assert len(events) == 0
    assert ack.get("code") == 200
    assert ack.get("message") == "Success"
