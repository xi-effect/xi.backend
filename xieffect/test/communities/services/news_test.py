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
def test_post_creation(client, socketio_client, test_community, list_tester):
    def get_posts_list(community_id: int) -> list[dict]:
        """Check the success of getting the list of posts"""
        result = check_code(
            client.get(
                f"/communities/{community_id}/news/index/",
                json={"counter": 20, "offset": 0},
            )
        ).get("results")
        assert isinstance(result, list)
        return result

    community_id_json = {"community_id": test_community}

    # Check successfully open news-room
    socketio_client.assert_emit_success("open-news", community_id_json)

    posts_ids = [d.get("id") for d in get_posts_list(test_community)]
    post_data = dict(title="tit", description="desc", **community_id_json)

    # Assert post creation
    result_data = socketio_client.assert_emit_ack("new-post", post_data)
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

    # Check correct update posts
    post_dict_list = [
        {},
        {"title": "new_title", "description": "new_description"},
        {"description": "the_newest_description"},
    ]
    post_ids = dict(post_id=post_id, **community_id_json)
    for post_upd in post_dict_list:
        post_upd = dict(post_upd, **post_ids)
        old_data = Post.find_by_id(post_id)
        upd_data = socketio_client.assert_emit_ack("update-post", post_upd)

        assert upd_data.get("id") == post_id
        assert upd_data.get("title") == post_upd.get("title") or old_data.title
        description = post_upd.get("description") or old_data.description
        assert upd_data.get("description") == description

    # Check successfully post delete
    socketio_client.assert_emit_success("delete-post", post_ids)
    posts_list = get_posts_list(test_community)
    assert isinstance(posts_list, list)
    assert len(posts_list) == 0

    # Check successfully close news-room
    socketio_client.assert_emit_success("close-news", community_id_json)

    # Check out community
    socketio_client.assert_emit_success("leave-community", community_id_json, callback=True)
