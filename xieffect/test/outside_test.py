from typing import Tuple

from flask.testing import FlaskClient
from pytest import mark
from werkzeug.test import TestResponse

from xieffect.test.conftest import TEST_EMAIL, BASIC_PASS
from xieffect.test.components import check_status_code, dict_equal
from xieffect.wsgi import generate_code, dumps_feedback, Invite, TEST_INVITE_ID

TEST_CREDENTIALS = {"email": TEST_EMAIL, "password": BASIC_PASS}


@mark.order(1)
def test_login(base_client: FlaskClient):
    response: TestResponse = check_status_code(base_client.post("/auth/", json=TEST_CREDENTIALS), get_json=False)
    assert "Set-Cookie" in response.headers.keys()
    cookie: Tuple[str, str] = response.headers["Set-Cookie"].partition("=")[::2]
    assert cookie[0] == "access_token_cookie"
    check_status_code(base_client.post("/logout/"))


@mark.order(10)
def test_signup(base_client: FlaskClient):
    credentials = {"email": "hey@hey.hey", "password": "12345", "username": "hey"}

    def assert_with_code(code: str, status: int, message: str):
        assert check_status_code(base_client.post("/reg/", json=dict(credentials, code=code)), status)["a"] == message

    assert_with_code("hey", 400, "Malformed code (BadSignature)")
    assert_with_code(Invite.serializer.dumps((-1, 0)), 404, "Invite not found")

    data = dict(credentials, code=Invite.serializer.dumps((TEST_INVITE_ID, 0)))
    response = check_status_code(base_client.post("/reg/", json=data), get_json=False)
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
    assert dict_equal(result[0], feedback, "data", "type")


@mark.order(50)
def test_invite_curds(client: FlaskClient, admin_client: FlaskClient, list_tester):
    def request_assert_admin(method, url: str, json=None):
        assert check_status_code(method(client, url, json=json), 403)["a"] == "Permission denied"
        return check_status_code(method(admin_client, url, json=json))

    invite_data = {"name": "test", "limit": -1, "accepted": 0}
    invite_data2 = {"name": "toast", "limit": 5, "accepted": 0}

    assert (invite_id := request_assert_admin(FlaskClient.post, "/invites/", invite_data).get("id", None)) is not None
    result = request_assert_admin(FlaskClient.get, f"/invites/{invite_id}/")
    assert dict_equal(result, invite_data, "name", "limit", "accepted")
    invite_data2["code"] = result["code"]

    results = request_assert_admin(FlaskClient.post, "/invites/index/", {"offset": 0})["results"]
    assert any(invite == result for invite in results), results

    assert request_assert_admin(FlaskClient.put, f"/invites/{invite_id}/", invite_data2)
    result = request_assert_admin(FlaskClient.get, f"/invites/{invite_id}/")
    assert dict_equal(result, invite_data2, "name", "limit", "accepted", "code")

    results = request_assert_admin(FlaskClient.post, "/invites/index/", {"offset": 0})["results"]
    assert any(invite == result for invite in results), results

    assert request_assert_admin(FlaskClient.delete, f"/invites/{invite_id}/")["a"]
    assert check_status_code(admin_client.get(f"/invites/{invite_id}/"), 404)["a"] == "Invite not found"

    results = request_assert_admin(FlaskClient.post, "/invites/index/", {"offset": 0})["results"]
    assert not any(invite == result for invite in results), results
