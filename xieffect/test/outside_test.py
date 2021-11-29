from typing import Tuple

from flask.testing import FlaskClient
from pytest import mark
from werkzeug.test import TestResponse

from xieffect.test.components import check_status_code
from xieffect.wsgi import generate_code, dumps_feedback


# @mark.order(0)
# def test_startup(base_client: FlaskClient):
#     assert check_status_code(base_client.get("/")) == {"hello": "word"}


@mark.order(1)
def test_login(base_client: FlaskClient):
    response: TestResponse = check_status_code(base_client.post("/auth/", follow_redirects=True, data={
        "email": "test@test.test",
        "password": "0a989ebc4a77b56a6e2bb7b19d995d185ce44090c" +
                    "13e2984b7ecc6d446d4b61ea9991b76a4c2f04b1b4d244841449454"}), get_json=False)
    assert "Set-Cookie" in response.headers.keys()
    cookie: Tuple[str, str] = response.headers["Set-Cookie"].partition("=")[::2]
    assert cookie[0] == "access_token_cookie"
    check_status_code(base_client.post("/logout/"))


def assert_feedback(client: FlaskClient, data: dict, a: str):
    assert check_status_code(client.post("/feedback/", json=data))["a"] == a


@mark.order(30)
def test_feedback(base_client: FlaskClient, client: FlaskClient):  # assumes user_id=1 (test) exists, user_id=-1 doesn't
    feedback = {"type": "general", "data": {"lol": "hey"}}

    assert_feedback(base_client, feedback, "Neither the user is authorized, nor the code is provided")
    assert_feedback(base_client, dict(feedback, code="lol"), "Bad code signature")
    assert_feedback(base_client, dict(feedback, code=generate_code(-1)), "Code refers to non-existing user")
    assert_feedback(base_client, dict(feedback, code=generate_code(1)), "Success")
    assert_feedback(client, feedback, "Success")

    result = dumps_feedback()
    assert len(result) == 2
    result[0].pop("id")
    result[1].pop("id")
    assert result[0] == result[1]
    assert result[0]["data"] == {"lol": "hey"}  # TODO use dict_equal after feat/socketio-test merge
    assert result[0]["type"] == "general"
