from pytest import mark
from flask import Response
from flask.testing import FlaskClient


@mark.order(8)
def test_missing_url(client: FlaskClient):
    response: Response = client.get("/this-does-not-exist")
    assert response.status_code == 404


@mark.order(9)
def test_missing_module(client: FlaskClient):
    response: Response = client.post("/modules/-1/report/", json={"reason": "It's so negative!"})
    assert response.status_code == 404
