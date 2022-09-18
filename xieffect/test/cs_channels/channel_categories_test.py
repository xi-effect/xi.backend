from __future__ import annotations

from flask.testing import FlaskClient
from flask_socketio import SocketIOTestClient
from pytest import mark

from __lib__.flask_fullstack import dict_equal, check_code


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
    categories_data = {"name": "cat", "description": "desc", "community_id": community_id, "position": 1}
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

    a = [None, 0, 1, 1, None, 0, None, 3, 2, None]
    for i in a:
        categories_data = {
            "name": f"cat{i}",
            "description": "desc",
            "community_id": community_id,
            "position": i
        }
        categories_id = assert_create_categories(socketio_client, categories_data)
        categories_ids.append(categories_id)

    cats = get_categories_list(client, community_id)
    assert cats[0]["id"] == 1 and cats[0]["prev-category-id"] == 9
    assert cats[3]["id"] == 4 and cats[3]["next-category-id"] == 2
    assert cats[5]["id"] == 6 and cats[5]["prev-category-id"] == 10
    assert cats[7]["id"] == 8 and cats[7]["next-category-id"] == 11
    assert cats[9]["id"] == 10 and cats[7]["prev-category-id"] == 6

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

    category_move = {"community_id": community_id, "category_id": 2, "position": 6}
    assert_move_category(socketio_client, category_move, client)

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
    old_date = get_categories_list(client, category_upd["community_id"])[0]
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
    client
):
    ack = socketio_client.emit("move-category", category_move, callback=True)
    events = socketio_client.get_received()
    assert len(events) == 0
    assert ack.get("code") == 200

    result_data = ack.get("data")
    assert result_data is not None
    assert result_data["id"] == 2
    assert result_data["prev-category-id"] == 6
    assert result_data["next-category-id"] == 8


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
