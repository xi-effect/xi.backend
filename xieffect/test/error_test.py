from __future__ import annotations

from pytest import mark

from test.conftest import FlaskTestClient


@mark.order(300)
def test_missing_url(client: FlaskTestClient):
    client.get("/this/does/not/exist/", expected_status=404, get_json=False)


@mark.order(301)
def test_missing_module(client: FlaskTestClient):
    client.post(
        "/modules/-1/report/",
        json={"reason": "It's so negative!"},
        expected_status=404,
        get_json=False,
    )


@mark.order(302)
def test_incomplete_request(base_client: FlaskTestClient):
    base_client.post("/signup/", expected_status=400, get_json=False)
