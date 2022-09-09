from flask.testing import FlaskClient

from pytest import mark

from __lib__.flask_fullstack import check_code

TEST_IDS = []
TEST_COMMUNITY = 1


# Create test news
@mark.order(1050)
@mark.parametrize("title, description, code",
                  [
                      ("post", "description", 200),
                      ("post", None, 200)
                  ])
def test_create_news(client: FlaskClient, title, description, code):
    global TEST_IDS
    response = check_code(client.post(f"/communities/{TEST_COMMUNITY}/news/index/",
                                      json={"title": title, "description": description}), code)
    assert response
    TEST_IDS.append(response["id"])


# Get news list
@mark.order(1051)
@mark.parametrize("counter, offset, code",
                  [
                      (20, 0, 200),
                      (None, 0, 200),
                      (None, None, 400),
                      (20, None, 200)
                  ]
                  )
def test_get_news_list(client: FlaskClient, counter, offset, code):
    response = check_code(client.get(f"/communities/{TEST_COMMUNITY}/news/index",
                                     json={"counter": counter, "offset": offset}), code)
    # Check code
    assert response

    if code != 400:
        news_list: dict = response["results"]

        if offset is None:
            # Check empty result for offset == None
            assert not news_list
        else:
            if counter:
                # Check parameters of post for successfully response
                assert news_list[0]["create-datetime"]
                assert news_list[0]["change-datetime"] == news_list[0]["create-datetime"]
                assert not news_list[0]["deleted"]
                assert news_list[0]["community-id"] == 1
