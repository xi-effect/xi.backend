from typing import Tuple

from flask.testing import FlaskClient
from pytest import fixture

from api import app, db
from flask.wrappers import Response


class RedirectedFlaskClient(FlaskClient):
    def open(self, *args, **kwargs):
        kwargs["follow_redirects"] = True
        return super(RedirectedFlaskClient, self).open(*args, **kwargs)


app.test_client_class = RedirectedFlaskClient


@fixture
def client():
    with app.test_client() as client:
        response: Response = client.post("/auth", follow_redirects=True, data={
            "email": "test@test.test",
            "password": "0a989ebc4a77b56a6e2bb7b19d995d185ce44090c" +
                        "13e2984b7ecc6d446d4b61ea9991b76a4c2f04b1b4d244841449454"})
        assert response.status_code == 200
        assert "Set-Cookie" in response.headers.keys()
        cookie: Tuple[str, str] = response.headers["Set-Cookie"].partition("=")[::2]
        assert cookie[0] == "access_token_cookie"
        client.set_cookie("test", "access_token_cookie", cookie[1])
        yield client


@fixture
def database():  # ???
    with app.app_context():
        yield db
