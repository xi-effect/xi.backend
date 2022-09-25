from __future__ import annotations

from pytest import mark, fixture

from __lib__.flask_fullstack import dict_equal, check_code
from common.testing import SocketIOTestClient
from communities.services.news_db import Post
from ..base.meta_test import assert_create_community

COMMUNITY_DATA = {"name": "test"}


@fixture
def test_community(socketio_client: SocketIOTestClient) -> int:
    # TODO place more globally (duplicate from invites_test)
    # TODO use yield & delete the community after
    return assert_create_community(socketio_client, COMMUNITY_DATA)


@mark.order(1100)
def test_post_creation(client, socketio_client, test_community):
    def assert_update_post(post_upd: dict):
        """Post update and validation"""
        old_date = Post.find_by_id(post_upd.get("post_id"))
        upd_ack = socketio_client.emit("update-post", post_upd, callback=True)
        upd_events = socketio_client.get_received()
        assert len(upd_events) == 0
        assert upd_ack.get("code") == 200

        upd_data = upd_ack.get("data")
        assert upd_data.get("id") == post_upd.get("post_id")

        if post_upd.get("title") is None:
            assert upd_data.get("title") == old_date.title
        else:
            assert upd_data.get("title") == post_upd.get("title")

        if post_upd.get("description") is None:
            if old_date.description is not None:
                assert upd_data.get("description") == old_date.description
            else:
                assert upd_data.get("description") is None
        else:
            assert upd_data.get("description") == post_upd.get("description")

    def get_posts_list(community_id):
        """Check the success of getting the list of posts"""
        result = check_code(
            client.get(
                f"/communities/{community_id}/news/index/",
                json={"counter": 20, "offset": 0}
            )
        ).get("results")
        assert isinstance(result, list)
        return result

    community_id_json = {"community_id": test_community}

    # Check successfully open news-room
    ack = socketio_client.emit("open-news", community_id_json, callback=True)
    events = socketio_client.get_received()
    assert len(events) == 0
    assert ack.get("code") == 200
    assert ack.get("message") == "Success"

    posts_ids = [d.get("id") for d in get_posts_list(test_community)]
    post_data = {"title": "tit", "description": "desc", "community_id": test_community}

    # Assert post creation
    ack = socketio_client.emit("new-post", post_data, callback=True)
    events = socketio_client.get_received()
    assert len(events) == 0
    assert ack.get("code") == 200
    result_data = ack.get("data")
    post_id = result_data.get("id")
    assert isinstance(post_id, int)
    assert dict_equal(result_data, post_data, "title", "description")

    posts_ids.append(post_id)

    # Check successfully post creation
    found = False
    for data in get_posts_list(test_community):
        assert data.get("id") in posts_ids
        if data.get("id") == post_id:
            assert not found
            assert dict_equal(data, post_data, "title", "description")
            assert data.get("created") == data.get("changed")
            assert Post.find_by_id(data.get("id")).deleted is False
            found = True
    assert found

    # Check post update
    post_update: dict = {"community_id": test_community, "post_id": post_id}
    assert_update_post(post_update)

    post_update1 = dict(post_update, title="new_title")
    assert_update_post(post_update1)
    post_update1["description"] = "new_description"
    assert_update_post(post_update1)

    post_update2 = dict(post_update, description="new_description2")
    assert_update_post(post_update2)

    # Check successfully post delete
    ack = socketio_client.emit("delete-post", post_update, callback=True)
    events = socketio_client.get_received()
    posts_list = get_posts_list(post_update.get("community_id"))
    assert len(events) == 0
    assert ack.get("code") == 200
    assert ack.get("message") == "Success"
    assert isinstance(posts_list, list)
    assert len(posts_list) == 0

    # Check successfully close news-room
    ack = socketio_client.emit("close-news", community_id_json, callback=True)
    events = socketio_client.get_received()
    assert len(events) == 0
    assert ack.get("code") == 200
    assert ack.get("message") == "Success"

    # Check out community
    ack = socketio_client.emit("leave-community", community_id_json, callback=True)
    assert dict_equal(ack, {"code": 200, "message": "Success"}, ("code", "message"))
    assert len(socketio_client.get_received()) == 0
