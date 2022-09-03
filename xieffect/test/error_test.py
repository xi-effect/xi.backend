from __future__ import annotations

from flask.testing import FlaskClient
from pytest import mark

from __lib__.flask_fullstack import check_code


@mark.order(300)
def test_missing_url(client: FlaskClient):
    check_code(client.get("/this/does/not/exist/"), 404, get_json=False)


@mark.order(301)
def test_missing_module(client: FlaskClient):
    check_code(client.post("/modules/-1/report/", json={"reason": "It's so negative!"}), 404, get_json=False)


@mark.order(302)
def test_incomplete_request(client: FlaskClient):
    check_code(client.post("/settings/"), 400, get_json=False)
