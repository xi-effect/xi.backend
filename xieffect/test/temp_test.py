from __future__ import annotations

from flask.testing import FlaskClient
from flask_fullstack import check_code, dict_equal
from pytest import mark

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
