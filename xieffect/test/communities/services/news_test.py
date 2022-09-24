from __future__ import annotations

from flask.testing import FlaskClient
from pytest import mark

from __lib__.flask_fullstack import dict_equal, check_code
from common.testing import SocketIOTestClient


@mark.order(1100)
def test_post_creation(client: FlaskClient, socketio_client: SocketIOTestClient):
    community_data = {"name": "12345", "description": "test"}
    community_id = assert_create_community(socketio_client, community_data)

    community_id_json = {"community_id": community_id}
    assert_open_news(socketio_client, community_id_json)

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
            assert data["created"] is not None
            assert data["created"] == data["changed"]
            assert data["deleted"] is False
            found_news = True
    assert found_news

    news_update: dict = {"community_id": community_id, "post_id": 1}
    assert_update_news(socketio_client, news_update, client)

    news_update1 = dict(news_update, title="new_title")
    assert_update_news(socketio_client, news_update1, client)
    news_update1["description"] = "new_description"
    assert_update_news(socketio_client, news_update1, client)

    news_update2 = dict(news_update, description="new_description2")
    assert_update_news(socketio_client, news_update2, client)

    assert_delete_news(socketio_client, news_update, client)

    assert_close_news(socketio_client, community_id_json)

    ack = socketio_client.emit("leave-community", community_id_json, callback=True)
    assert dict_equal(ack, {"code": 200, "message": "Success"}, ("code", "message"))
    assert len(socketio_client.get_received()) == 0


def assert_create_news(socketio_client: SocketIOTestClient, news_data: dict):
    ack = socketio_client.emit("new-post", news_data, callback=True)
    events = socketio_client.get_received()
    assert len(events) == 0
    assert ack.get("code") == 200

    result_data = ack.get("data")
    assert result_data is not None

    news_id = result_data.get("id")
    assert isinstance(news_id, int)
    assert dict_equal(result_data, news_data, "title", "description")

    return news_id


def assert_update_news(socketio_client: SocketIOTestClient, news_upd: dict, client):
    ack = socketio_client.emit("update-post", news_upd, callback=True)
    events = socketio_client.get_received()
    old_date = get_news_list(client, news_upd["community_id"])[0]
    assert len(events) == 0
    assert ack.get("code") == 200

    result_data = ack.get("data")
    assert result_data is not None
    assert result_data["id"] == news_upd["post_id"]

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
    assert ack.get("code") == 200
    assert ack.get("message") == "Success"
    assert isinstance(old_date, list)
    assert len(old_date) == 0


def get_news_list(client: FlaskClient, community_id):
    result = check_code(
        client.get(
            f"/communities/{community_id}/news/index/",
            json={"counter": 20, "offset": 0}
        )
    ).get("results")
    assert isinstance(result, list)
    return result


def assert_open_news(socketio_client: SocketIOTestClient, community_id: dict):
    ack = socketio_client.emit("open-news", community_id, callback=True)
    events = socketio_client.get_received()
    assert len(events) == 0
    assert ack.get("code") == 200
    assert ack.get("message") == "Success"


def assert_close_news(socketio_client: SocketIOTestClient, community_id: dict):
    ack = socketio_client.emit("close-news", community_id, callback=True)
    events = socketio_client.get_received()
    assert len(events) == 0
    assert ack.get("code") == 200
    assert ack.get("message") == "Success"
