from typing import Tuple, Iterator, Callable

from flask.testing import FlaskClient
from pytest import fixture
from werkzeug.test import TestResponse

from wsgi import application as app, TEST_EMAIL, BASIC_PASS  # temp, return back to ``from api import app``
from xieffect.test.components import check_status_code


class RedirectedFlaskClient(FlaskClient):
    def open(self, *args, **kwargs):
        kwargs["follow_redirects"] = True
        return super(RedirectedFlaskClient, self).open(*args, **kwargs)


app.test_client_class = RedirectedFlaskClient


@fixture
def base_client():
    app.debug = True
    with app.test_client() as client:
        yield client


def login(client: FlaskClient, email: str, password: str) -> FlaskClient:
    response: TestResponse = client.post("/auth/", follow_redirects=True, data={"email": email, "password": password})
    assert response.status_code == 200
    assert "Set-Cookie" in response.headers.keys()
    cookie: Tuple[str, str] = response.headers["Set-Cookie"].partition("=")[::2]
    assert cookie[0] == "access_token_cookie"
    client.set_cookie("test", "access_token_cookie", cookie[1])
    return client


@fixture
def client(base_client: FlaskClient) -> FlaskClient:
    return login(base_client, TEST_EMAIL, BASIC_PASS)


@fixture()
def multi_client(base_client: FlaskClient) -> Callable[[str], FlaskClient]:
    def multi_client_inner(user_email: str):
        return login(base_client, user_email, BASIC_PASS)

    return multi_client_inner


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
