from __future__ import annotations

from flask.testing import FlaskClient
from pytest import mark

from __lib__.flask_fullstack import check_code, dict_equal
from users import dumps_feedback, generate_code


def assert_feedback(client: FlaskClient, data: dict, a: str):
    assert check_code(client.post("/feedback/", json=data))["a"] == a


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
def test_invite_curds(client: FlaskClient, admin_client: FlaskClient):
    def request_assert_admin(method, url: str, json=None):
        assert check_code(method(client, url, json=json), 403)["a"] == "Permission denied"
        return check_code(method(admin_client, url, json=json))

    invite_data = {"name": "test", "limit": -1, "accepted": 0}
    invite_data2 = {"name": "toast", "limit": 5, "accepted": 0}

    assert (invite_id := request_assert_admin(FlaskClient.post, "/invites/", invite_data).get("id")) is not None
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
    assert check_code(admin_client.get(f"/invites/{invite_id}/"), 404)["a"] == "Invite not found"

    results = request_assert_admin(FlaskClient.post, "/invites/index/", {"offset": 0})["results"]
    assert not any(invite == result for invite in results), results
