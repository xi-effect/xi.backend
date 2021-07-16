import pytest
from flask.testing import FlaskClient
from flask.wrappers import Response

from xieffect.api import app


@pytest.fixture
def client():
    with app.test_client() as client:
        yield client


def test_startup(client: FlaskClient):
    response: Response = client.get("/")
    assert response.status_code == 200
    assert response.get_json() == {"hello": "word"}


def test_login(client: FlaskClient):
    response: Response = client.post("/auth", follow_redirects=True, data={
        "email": "test@test.test",
        "password": "0a989ebc4a77b56a6e2bb7b19d995d185ce44090c" +
                    "13e2984b7ecc6d446d4b61ea9991b76a4c2f04b1b4d244841449454"})
    assert response.status_code == 200
    assert "Set-Cookie" in response.headers.keys()
    assert response.headers["Set-Cookie"].startswith("access_token_cookie=")
