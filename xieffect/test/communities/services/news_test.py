from __future__ import annotations

from flask_fullstack import dict_equal, check_code
from pytest import mark

from common.testing import SocketIOTestClient
from communities.services.news_db import Post
from ..base.invites_test import create_assert_successful_join


def get_posts_list(client, community_id: int) -> list[dict]:
    """Check the success of getting the list of posts"""
    result = check_code(
        client.get(
            f"/communities/{community_id}/news/index/",
            json={"counter": 20, "offset": 0},
        )
    ).get("results")
    assert isinstance(result, list)
    return result


@mark.order(1100)
def test_post_creation(
    client,
    multi_client,
    list_tester,
    socketio_client,
    test_community,
):  # TODO redo without calls to the database
    # Create second owner & base clients
    socketio_client2 = SocketIOTestClient(client)

    invite_data = {
        "community_id": test_community,
        "role": "base",
        "limit": 2,
        "days": 10,
    }
    invite = socketio_client.assert_emit_ack("new_invite", invite_data)
    member = multi_client("1@user.user")
    sio_member = SocketIOTestClient(member)
    assert_successful_join = create_assert_successful_join(
        list_tester,
        test_community,
    )
    assert_successful_join(member, invite["id"], invite["code"], sio_member)

    community_id_json = {"community_id": test_community}

    # Check successfully open news-room
    for user in (socketio_client, socketio_client2, sio_member):
        user.assert_emit_success("open_news", community_id_json)

    posts_ids = [d.get("id") for d in get_posts_list(client, test_community)]
    post_data = dict(community_id_json, title="tit", description="desc")

    # Assert post creation
    result_data = socketio_client.assert_emit_ack("new_post", post_data)
    post_id = result_data.get("id")
    assert isinstance(post_id, int)
    assert dict_equal(result_data, post_data, "title", "description")
    for user in (socketio_client2, sio_member):
        user.assert_only_received("new_post", result_data)
    posts_ids.append(post_id)

    # Check successfully post creation
    found = False
    for data in get_posts_list(client, test_community):
        assert data.get("id") in posts_ids
        if data.get("id") == post_id:
            assert not found
            assert dict_equal(data, post_data, "title", "description")
            assert data.get("created") == data.get("changed")
            # TODO redo without calls to the database (separate into functional tests)
            assert Post.find_by_id(data.get("id")).deleted is False
            found = True
    assert found

    # Check correct update posts
    post_dict_list = [
        {},
        {"title": "new_title", "description": "new_description"},
        {"description": "the_newest_description"},
    ]
    post_ids = dict(community_id_json, post_id=post_id)
    for post_upd in post_dict_list:
        post_upd = dict(post_upd, **post_ids)

        old_data = Post.find_by_id(post_id)  # TODO redo without calls to the database
        old_title: str = old_data.title
        old_description: str = old_data.description

        upd_data = socketio_client.assert_emit_ack("update_post", post_upd)
        assert upd_data.get("id") == post_id
        assert upd_data.get("title") == post_upd.get("title") or old_title
        description = post_upd.get("description") or old_description
        assert upd_data.get("description") == description

        for user in (socketio_client2, sio_member):
            user.assert_only_received("update_post", upd_data)

    # Check successfully post delete
    socketio_client.assert_emit_success("delete_post", post_ids)
    for user, sio_user in ((client, socketio_client2), (member, sio_member)):
        posts_list = get_posts_list(user, test_community)
        assert isinstance(posts_list, list)
        assert len(posts_list) == 0
        sio_user.assert_only_received("delete_post", post_ids)

    # Check successfully close news-room
    for user in (socketio_client, socketio_client2, sio_member):
        user.assert_emit_success("close_news", community_id_json)
