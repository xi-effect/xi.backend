from flask.testing import FlaskClient

from pytest import mark

from random import choice

from __lib__.flask_fullstack import check_code
from .news_lister_test import TEST_IDS, TEST_COMMUNITY


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
    assert update_post["created"] == post["created"]
    assert update_post["changed"] != post["changed"]
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
