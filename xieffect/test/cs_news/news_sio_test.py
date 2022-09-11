from __future__ import annotations

from flask.testing import FlaskClient
from flask_socketio import SocketIOTestClient
from pytest import mark

from __lib__.flask_fullstack import dict_equal, check_code


def assert_create_community(socketio_client: SocketIOTestClient, community_data: dict):
    ack = socketio_client.emit("new-community", community_data, callback=True)
    events = socketio_client.get_received()
    assert len(events) == 0
    assert ack.get("code", None) == 200

    result_data = ack.get("data", None)
    assert result_data is not None

    community_id = result_data.get("id", None)
    assert isinstance(community_id, int)
    assert dict_equal(result_data, community_data, *community_data.keys())
    return community_id


def assert_create_news(socketio_client: SocketIOTestClient, news_data: dict):
    ack = socketio_client.emit("new-post", news_data, callback=True)
    events = socketio_client.get_received()
    assert len(events) == 0
    assert ack.get("code", None) == 200

    result_data = ack.get("data", None)
    assert result_data is not None

    news_id = result_data.get("id", None)
    assert isinstance(news_id, int)
    assert dict_equal(result_data, news_data, "title", "description")

    return news_id


def assert_update_news(socketio_client: SocketIOTestClient, news_upd: dict, client):
    ack = socketio_client.emit("update-post", news_upd, callback=True)
    events = socketio_client.get_received()
    old_date = get_news_list(client, news_upd["community_id"])[0]
    assert len(events) == 0
    assert ack.get("code", None) == 200

    result_data = ack.get("data", None)
    assert result_data is not None
    assert result_data["id"] == news_upd["entry_id"]

    if news_upd.get("title") is None:
        assert result_data["title"] == old_date["title"]
    else:
        assert result_data["title"] == news_upd["title"]

    if news_upd.get("description") is None:
        if old_date.get("description") is not None:
            assert result_data["description"] == old_date["description"]
        else:
            assert result_data.get("description") is None
    else:
        assert result_data["description"] == news_upd["description"]


def assert_delete_news(socketio_client: SocketIOTestClient, news_del: dict, client):
    ack = socketio_client.emit("delete-post", news_del, callback=True)
    events = socketio_client.get_received()
    old_date = get_news_list(client, news_del["community_id"])
    assert len(events) == 0
    assert ack.get("code", None) == 200
    assert ack.get("data", None) == {"a": "Post was successfully deleted"}
    assert old_date == []


def get_communities_list(client: FlaskClient):
    result = check_code(client.get("/home/")).get("communities", None)
    assert isinstance(result, list)
    return result


def get_news_list(client: FlaskClient, community_id):
    result = check_code(
        client.get(
            f"/communities/{community_id}/news/index",
            json={"counter": 20, "offset": 0}
        )
    ).get("results", None)
    assert isinstance(result, list)
    return result


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

    news_ids = [d["id"] for d in get_news_list(client, community_id)]
    news_data = {"title": "tit", "description": "desc", "community_id": community_id}
    news_id = assert_create_news(socketio_client, news_data)
    news_ids.append(news_id)

    found_news = False
    for data in get_news_list(client, community_id):
        assert data["id"] in news_ids
        if data["id"] == news_id:
            assert not found_news
            assert dict_equal(data, news_data, "title", "description")
            assert data["created"] == data["changed"] is not None
            assert data["deleted"] is False
            found_news = True
    assert found_news

    news_upd = {"community_id": community_id, "entry_id": 1}
    assert_update_news(socketio_client, news_upd, client)

    news_upd1 = news_upd.copy()
    news_upd1["title"] = "new_title"
    assert_update_news(socketio_client, news_upd1, client)
    news_upd1["description"] = "new_desc"
    assert_update_news(socketio_client, news_upd1, client)

    news_upd2 = news_upd.copy()
    news_upd2["description"] = "new_desc2"
    assert_update_news(socketio_client, news_upd2, client)

    assert_delete_news(socketio_client, news_upd, client)
