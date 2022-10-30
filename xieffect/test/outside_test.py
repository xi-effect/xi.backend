from __future__ import annotations

from flask.testing import FlaskClient
from flask_fullstack import check_code, dict_equal
from flask_mail import Message
from pytest import mark, skip
from werkzeug.test import TestResponse

from common import mail, mail_initialized
from other import EmailType
from wsgi import Invite, TEST_INVITE_ID
from .conftest import BASIC_PASS, TEST_EMAIL, SocketIOTestClient

TEST_CREDENTIALS = {"email": TEST_EMAIL, "password": BASIC_PASS}  # noqa: WPS407


@mark.order(1)
def test_login(base_client: FlaskClient):
    response: TestResponse = check_code(base_client.post("/auth/", json=TEST_CREDENTIALS), get_json=False)

    result: dict[str, ...] = response.json
    assert result.pop("a", None) == "Success"
    for key in ("communities", "user"):
        assert key in result
    for key in ("id", "username", "dark-theme", "language"):
        assert key in result["user"]

    assert "Set-Cookie" in response.headers
    cookie: tuple[str, str] = response.headers["Set-Cookie"].partition("=")[::2]
    assert cookie[0] == "access_token_cookie"

    check_code(base_client.post("/logout/"))


@mark.order(10)
def test_signup(base_client: FlaskClient):
    credentials = {"email": "hey@hey.hey", "password": "12345", "username": "hey"}
    default_data = {"username": credentials["username"], "dark-theme": True, "language": "russian"}

    def assert_with_code(code: str, status: int, message: str):
        assert check_code(base_client.post("/reg/", json=dict(credentials, code=code)), status)["a"] == message

    with mail.record_messages() as outbox:
        # Checking fails
        assert_with_code("hey", 400, "Malformed code (BadSignature)")
        assert_with_code(Invite.serializer.dumps((-1, 0)), 404, "Invite not found")

        assert not mail_initialized or len(outbox) == 0

    # Checking successful reg
    data = dict(credentials, code=Invite.serializer.dumps((TEST_INVITE_ID, 0)))
    response = check_code(base_client.post("/reg/", json=data), get_json=False)

    # Checking the returned data
    result: dict[str, ...] = response.json
    assert result.pop("a", None) == "Success"

    communities = result.get("communities")
    assert isinstance(communities, list)
    assert len(communities) == 0

    user = result.get("user")
    assert isinstance(user, dict)
    assert dict_equal(user, default_data, *default_data.keys())
    assert "id" in user

    # Checking for cookies
    assert "Set-Cookie" in response.headers
    cookie: tuple[str, str] = response.headers["Set-Cookie"].partition("=")[::2]
    assert cookie[0] == "access_token_cookie"

    # Check the /home/ as well
    response = check_code(base_client.get("/home/"))
    assert response == result

    check_code(base_client.post("/logout/"))


@mark.order(12)
def test_email_confirm(base_client: FlaskClient):
    if not mail_initialized:
        skip("Email module is not setup")

    a = [1, 2, 3, 4]
    assert 1 in a

    # TODO use hey@hey.hey but delete account form test_signup (& here)
    credentials = {
        "email": "hey2@hey.hey",
        "password": "12345",
        "username": "hey",
        "code": Invite.serializer.dumps((TEST_INVITE_ID, 0))
    }
    link_start = "https://xieffect.ru/email/"

    with mail.record_messages() as outbox:
        assert check_code(base_client.post("/reg/", json=credentials))["a"] == "Success"

        assert len(outbox) == 1
        message: Message = outbox[0]
        assert message.subject == EmailType.CONFIRM.theme
        assert link_start in message.html

        code = message.html.partition(link_start)[2].partition('/"')[0]
        assert code != ""

        recipients = message.recipients
        assert len(recipients) == 1
        assert recipients[0] == credentials["email"]

    assert check_code(base_client.get("/settings/")).get("email-confirmed") is False
    assert check_code(base_client.post(f"/email-confirm/{code}/"))["a"] == "Success"
    assert check_code(base_client.get("/settings/")).get("email-confirmed") is True

    check_code(base_client.post("/logout/"))


@mark.order(15)
def test_sio_connection(client: FlaskClient):
    sio_client = SocketIOTestClient(client)
    assert sio_client.connected.get("/") is True


@mark.order(16)
def test_sio_unauthorized(base_client: FlaskClient):
    sio_client = SocketIOTestClient(base_client)
    assert sio_client.connected.get("/") is False
