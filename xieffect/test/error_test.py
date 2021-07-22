from flask import Response
from flask.testing import FlaskClient


def test_missing_url(client: FlaskClient):
    response: Response = client.get("/this-does-not-exist")
    assert response.status_code == 404


def test_missing_module(client: FlaskClient):
    response: Response = client.post("/modules/-1/report/", json={"reason": "It's so negative!"})
    assert response.status_code == 404
