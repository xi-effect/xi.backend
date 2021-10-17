from typing import Tuple, Iterator, Callable

from flask.testing import FlaskClient
from pytest import fixture
from werkzeug.test import TestResponse

from wsgi import application as app   # temp, return back to ``from api import app``
from xieffect.test.components import check_status_code


class RedirectedFlaskClient(FlaskClient):
    def open(self, *args, **kwargs):
        kwargs["follow_redirects"] = True
        return super(RedirectedFlaskClient, self).open(*args, **kwargs)


app.test_client_class = RedirectedFlaskClient


@fixture
def client():
    app.debug = True
    with app.test_client() as client:
        response: TestResponse = client.post("/auth/", follow_redirects=True, data={
            "email": "test@test.test",
            "password": "0a989ebc4a77b56a6e2bb7b19d995d185ce44090c" +
                        "13e2984b7ecc6d446d4b61ea9991b76a4c2f04b1b4d244841449454"})
        assert response.status_code == 200
        assert "Set-Cookie" in response.headers.keys()
        cookie: Tuple[str, str] = response.headers["Set-Cookie"].partition("=")[::2]
        assert cookie[0] == "access_token_cookie"
        client.set_cookie("test", "access_token_cookie", cookie[1])
        yield client


@fixture()
def list_tester(client: FlaskClient) -> Callable[[str, dict, int, int], Iterator[dict]]:
    def list_tester_inner(link: str, request_json: dict, page_size: int, status_code: int = 200) -> Iterator[dict]:
        counter = 0
        amount = page_size
        while amount == page_size:
            request_json["counter"] = counter
            response_json: dict = check_status_code(client.post(link, json=request_json), status_code)

            assert isinstance(response_json, list)
            for content in response_json:
                yield content

            amount = len(response_json)
            assert amount <= page_size

            counter += 1

        assert counter > 0

    return list_tester_inner
