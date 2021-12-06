from time import sleep
from typing import Union

from flask.testing import FlaskClient
from pytest import fixture

from run import socketio, app, Session
from .library2 import MultiClient as _MultiClient, DoubleClient, SocketIOTestClient

TEST_EMAIL: str = "test@test.test"
ADMIN_EMAIL: str = "admin@admin.admin"

BASIC_PASS: str = "0a989ebc4a77b56a6e2bb7b19d995d185ce44090c13e2984b7ecc6d446d4b61ea9991b76a4c2f04b1b4d244841449454"
ADMIN_PASS: str = "2b003f13e43546e8b416a9ff3c40bc4ba694d0d098a5a5cda2e522d9993f47c7b85b733b178843961eefe9cfbeb287fe"

Session.testing = True


class RedirectedFlaskClient(FlaskClient):
    def open(self, *args, **kwargs):
        kwargs["follow_redirects"] = True
        return super(RedirectedFlaskClient, self).open(*args, **kwargs)


app.test_client_class = RedirectedFlaskClient


class MultiClient(_MultiClient):
    def auth_user(self, email: str, password: str) -> Union[DoubleClient, None]:
        flask_client = app.test_client()
        response = flask_client.post(f"/auth/", json={"email": email, "password": password})
        assert response.status_code == 200 and response.get_json() == {"a": True}, response.get_json()
        sleep(1)
        return self.connect_user(flask_client)

    def attach_auth_user(self, username: str, email: str, password: str) -> bool:
        if (client := self.auth_user(email, password)) is not None:
            self.users[username] = client
            return True
        return False

    def get_tr_io(self, i: str = "1") -> tuple[SocketIOTestClient, SocketIOTestClient, SocketIOTestClient]:
        return self.users["Anatol-" + i].sio, self.users["Evgen-" + i].sio, self.users["Vasil-" + i].sio

    def get_dtr_io(self) -> tuple[SocketIOTestClient, SocketIOTestClient, SocketIOTestClient,
                                  SocketIOTestClient, SocketIOTestClient, SocketIOTestClient]:
        return *self.get_tr_io("1"), *self.get_tr_io("2")  # noqa # I know better


@fixture(scope="session", autouse=True)
def multi_client():
    with MultiClient(app, socketio) as multi_client:
        yield multi_client


@fixture()
def socket_tr_io_client():  # add to library2.py
    with MultiClient(app, socketio) as multi_client:
        multi_client.attach_auth_user("Anatol-1", "8@user.user", BASIC_PASS)
        multi_client.attach_auth_user("Anatol-2", "8@user.user", BASIC_PASS)
        multi_client.attach_auth_user("Evgen-1", "test@test.test", BASIC_PASS)
        multi_client.attach_auth_user("Evgen-2", "test@test.test", BASIC_PASS)
        multi_client.attach_auth_user("Vasil-1", "7@user.user", BASIC_PASS)
        multi_client.attach_auth_user("Vasil-2", "7@user.user", BASIC_PASS)
        yield multi_client
