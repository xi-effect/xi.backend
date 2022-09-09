from flask.testing import FlaskClient

from pytest import mark

from random import choice

from __lib__.flask_fullstack import check_code
from .news_lister_test import TEST_IDS, TEST_COMMUNITY
from communities.services.news_rst import Post
from common import sessionmaker


# Update test news
@mark.order(1052)
@mark.parametrize("title, description, code",
                  [
                      ("first new title", None, 200),
                      (None, "first new description", 200),
                      ("second new title", "second new description", 200),
                      (None, None, 200)
                  ]
                  )
def test_update_news(client: FlaskClient, title, description, code):
    post_id = choice(TEST_IDS)
    post = check_code(client.get(f"/communities/{TEST_COMMUNITY}/news/{post_id}/"), code)
    update_post = check_code(client.put(f"/communities/{TEST_COMMUNITY}/news/{post_id}/",
                                        json={"title": title, "description": description}), code)
    # Check codes
    assert post
    assert update_post

    post: dict = post
    update_post: dict = update_post

    if title is None:
        # Check if the old title is saved
        assert update_post["title"] == post["title"]
    else:
        # Check update title with new data
        assert update_post["title"] == title

    if description is None:
        if "description" in post:
            # Check if the old description is saved
            assert update_post["description"] == post["description"]
        else:
            # Check the absence description in the post
            assert "description" not in update_post
    else:
        # Check update description with new data
        assert update_post["description"] == description

    # Check saving other data
    assert update_post["create-datetime"] == post["create-datetime"]
    assert update_post["change-datetime"] != post["change-datetime"]
    assert update_post["deleted"] == post["deleted"]
    assert update_post["community-id"] == post["community-id"]
    assert update_post["user-id"] == post["user-id"]


# Soft-delete test news
@mark.order(1053)
def test_soft_delete_news(client: FlaskClient):
    post_id = choice(TEST_IDS)
    post = check_code(client.get(f"/communities/{TEST_COMMUNITY}/news/{post_id}/"), 200)
    delete = check_code(client.delete(f"/communities/{TEST_COMMUNITY}/news/{post_id}/"), 200)
    deleted_post = check_code(client.get(f"/communities/{TEST_COMMUNITY}/news/{post_id}/"), 200)

    # Check codes
    assert post
    assert deleted_post

    # Check the right deleted-status
    assert not post["deleted"]
    assert deleted_post["deleted"]

    # Check the right response of server
    assert delete["a"] == "News was successfully deleted"

    # Clear database before tests
    @sessionmaker.with_begin
    def clear(session):
        for ids in TEST_IDS:
            post_for_delete = Post.find_by_id(session, ids)

            session.delete(post_for_delete)
            session.flush()

            # Check the absence test news in the database
            assert check_code(client.get(f"/communities/{TEST_COMMUNITY}/news/{ids}/"), 404)
