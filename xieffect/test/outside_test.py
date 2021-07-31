from typing import Tuple

from pytest import fixture, mark
from flask.testing import FlaskClient
from flask.wrappers import Response

from api import app


@fixture
def base_client():
    with app.test_client() as client:
        yield client


@mark.order(1)
def test_startup(base_client: FlaskClient):
    response: Response = base_client.get("/")
    assert response.status_code == 200
    assert response.get_json() == {"hello": "word"}


@mark.order(2)
def test_login(base_client: FlaskClient):
    response: Response = base_client.post("/auth", follow_redirects=True, data={
        "email": "test@test.test",
        "password": "0a989ebc4a77b56a6e2bb7b19d995d185ce44090c" +
                    "13e2984b7ecc6d446d4b61ea9991b76a4c2f04b1b4d244841449454"})
    assert response.status_code == 200
    assert "Set-Cookie" in response.headers.keys()
    cookie: Tuple[str, str] = response.headers["Set-Cookie"].partition("=")[::2]
    assert cookie[0] == "access_token_cookie"
    base_client.set_cookie("test", "access_token_cookie", cookie[1])