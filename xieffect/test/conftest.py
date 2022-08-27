from typing import Tuple, Iterator, Callable, Protocol

from flask.testing import FlaskClient
from flask_socketio import SocketIOTestClient
from pytest import fixture
from werkzeug.test import TestResponse

from __lib__.flask_fullstack import check_code
from api import socketio
from wsgi import application as app, TEST_EMAIL, BASIC_PASS, ADMIN_EMAIL, ADMIN_PASS, TEST_MOD_NAME, TEST_PASS


# from .library2 import MultiClient as _MultiClient, DoubleClient, SocketIOTestClient


class RedirectedFlaskClient(FlaskClient):
    def open(self, *args, **kwargs):  # noqa: A003
        kwargs["follow_redirects"] = True
        return super(RedirectedFlaskClient, self).open(*args, **kwargs)


app.test_client_class = RedirectedFlaskClient


@fixture(scope="session", autouse=True)
def base_client():
    app.debug = True
    with app.test_client() as client:
        yield client


def base_login(client: FlaskClient, account: str, password: str, mub: bool = False) -> None:
    response: TestResponse = client.post("/mub/sign-in/" if mub else "/auth/",
                                         data={"username" if mub else "email": account, "password": password})
    assert response.status_code == 200
    assert "Set-Cookie" in response.headers.keys()
    cookie: Tuple[str, str] = response.headers["Set-Cookie"].partition("=")[::2]
    assert cookie[0] == "access_token_cookie"
    client.set_cookie("test", "access_token_cookie", cookie[1])


def login(account: str, password: str, mub: bool = False) -> FlaskClient:
    with app.test_client() as client:
        base_login(client, account, password, mub)
        return client


@fixture
def client() -> FlaskClient:
    return login(TEST_EMAIL, BASIC_PASS)


@fixture
def mod_client() -> FlaskClient:
    return login(TEST_MOD_NAME, TEST_PASS, True)


@fixture
def full_client() -> FlaskClient:
    client = login(TEST_EMAIL, BASIC_PASS)
    base_login(client, TEST_MOD_NAME, TEST_PASS, True)
    return client


def socketio_client_factory(client: FlaskClient) -> SocketIOTestClient:
    return socketio.test_client(app, flask_test_client=client)


@fixture
def socketio_client(client: FlaskClient) -> SocketIOTestClient:
    return socketio_client_factory(client)


@fixture
def admin_client() -> FlaskClient:
    return login(ADMIN_EMAIL, ADMIN_PASS)


@fixture
def multi_client() -> Callable[[str], FlaskClient]:
    def multi_client_inner(user_email: str):
        return login(user_email, BASIC_PASS)

    return multi_client_inner


class ListTesterProtocol(Protocol):
    def __call__(self, link: str, request_json: dict, page_size: int, status_code: int = 200, /) -> Iterator[dict]:
        pass


@fixture
def list_tester(full_client: FlaskClient) -> ListTesterProtocol:
    def list_tester_inner(link: str, request_json: dict, page_size: int, status_code: int = 200) -> Iterator[dict]:
        counter = 0
        amount = page_size
        while amount == page_size:
            request_json["counter"] = counter
            response_json: dict = check_code(full_client.post(link, json=request_json), status_code)

            assert "results" in response_json
            assert isinstance(response_json["results"], list)
            for content in response_json["results"]:
                yield content

            amount = len(response_json["results"])
            assert amount <= page_size

            counter += 1

        assert counter > 0

    return list_tester_inner

# class MultiClient(_MultiClient):
#     def auth_user(self, email: str, password: str) -> Union[DoubleClient, None]:
#         raise NotImplementedError
#
#     def attach_auth_user(self, username: str, email: str, password: str) -> bool:
#         if (client := self.auth_user(email, password)) is not None:
#             self.users[username] = client
#             return True
#         return False
#
#     def get_tr_io(self, i: str = "1") -> tuple[SocketIOTestClient, SocketIOTestClient, SocketIOTestClient]:
#         return self.users["Anatol-" + i].sio, self.users["Evgen-" + i].sio, self.users["Vasil-" + i].sio
#
#     def get_dtr_io(self) -> tuple[SocketIOTestClient, SocketIOTestClient, SocketIOTestClient,
#                                   SocketIOTestClient, SocketIOTestClient, SocketIOTestClient]:
#         return *self.get_tr_io("1"), *self.get_tr_io("2")  # noqa # I know better
#
#
# @fixture(scope="session", autouse=True)
# def multi_client():
#     with MultiClient(app, socketio) as multi_client:
#         yield multi_client
#
#
# @fixture()
# def socket_tr_io_client():  # add to library2.py
#     with MultiClient(app, socketio) as multi_client:
#         multi_client.attach_auth_user("Anatol-1", "8@user.user", BASIC_PASS)
#         multi_client.attach_auth_user("Anatol-2", "8@user.user", BASIC_PASS)
#         multi_client.attach_auth_user("Evgen-1", "test@test.test", BASIC_PASS)
#         multi_client.attach_auth_user("Evgen-2", "test@test.test", BASIC_PASS)
#         multi_client.attach_auth_user("Vasil-1", "7@user.user", BASIC_PASS)
#         multi_client.attach_auth_user("Vasil-2", "7@user.user", BASIC_PASS)
#         yield multi_client
