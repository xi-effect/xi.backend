from __future__ import annotations

from flask.testing import FlaskClient
from flask_fullstack import check_code, dict_equal
from flask_mail import Message
from pytest import mark
from werkzeug.test import TestResponse

from other import EmailType
from wsgi import Invite, TEST_INVITE_ID, socketio
from .conftest import BASIC_PASS, TEST_EMAIL, SocketIOTestClient

TEST_CREDENTIALS = {"email": TEST_EMAIL, "password": BASIC_PASS}  # noqa: WPS407


@mark.order(0)
def test_rest_docs(base_client: FlaskClient):
    result = check_code(base_client.get("/doc/"), get_json=False)
    assert "text/html" in result.content_type


@mark.order(1)
def test_sio_docs(base_client: FlaskClient):
    result = check_code(base_client.get("/asyncapi.json"))
    assert result == socketio.docs()


@mark.order(10)
def test_login(base_client: FlaskClient):
    response: TestResponse = check_code(base_client.post("/signin/", json=TEST_CREDENTIALS), get_json=False)

    result: dict[str, ...] = response.json
    assert result.pop("a", None) == "Success"
    for key in ("communities", "id", "username"):
        assert key in result
    assert "Set-Cookie" in response.headers
    cookie: tuple[str, str] = response.headers["Set-Cookie"].partition("=")[::2]
    assert cookie[0] == "access_token_cookie"

    check_code(base_client.post("/signout/"))


@mark.order(11)
def test_signup(base_client: FlaskClient, mock_mail):
    credentials = {"email": "hey@hey.hey", "password": "12345", "username": "hey"}

    def assert_with_code(code: str, status: int, message: str):
        assert check_code(base_client.post("/signup/", json=dict(credentials, code=code)), status)["a"] == message

    # Checking fails
    assert_with_code("hey", 400, "Malformed code (BadSignature)")
    assert_with_code(Invite.serializer.dumps((-1, 0)), 404, "Invite not found")
    assert len(mock_mail) == 0

    # Checking successful singup
    data = dict(credentials, code=Invite.serializer.dumps((TEST_INVITE_ID, 0)))
    response = check_code(base_client.post("/signup/", json=data), get_json=False)

    # Checking the returned data
    result: dict[str, ...] = response.json
    assert result.pop("a", None) == "Success"

    communities = result.get("communities")
    assert isinstance(communities, list)
    assert len(communities) == 0

    assert isinstance(result, dict)
    assert dict_equal(result, credentials, "username")
    assert "id" in result

    # Checking for cookies
    assert "Set-Cookie" in response.headers
    cookie: tuple[str, str] = response.headers["Set-Cookie"].partition("=")[::2]
    assert cookie[0] == "access_token_cookie"

    # Check the /home/ as well
    response = check_code(base_client.get("/home/"))
    assert response == result

    check_code(base_client.post("/signout/"))


@mark.order(12)
def test_email_confirm(base_client: FlaskClient, mock_mail):
    # TODO use hey@hey.hey but delete account form test_signup (& here)
    credentials = {
        "email": "hey2@hey.hey",
        "password": "12345",
        "username": "hey",
        "code": Invite.serializer.dumps((TEST_INVITE_ID, 0))
    }
    link_start = "https://xieffect.ru/email/"

    assert check_code(base_client.post("/signup/", json=credentials))["a"] == "Success"

    assert len(mock_mail) == 1
    message: Message = mock_mail[0]
    assert message.subject == EmailType.CONFIRM.theme
    assert link_start in message.html

    code = message.html.partition(link_start)[2].partition('/"')[0]
    assert code != ""

    recipients = message.recipients
    assert len(recipients) == 1
    assert recipients[0] == credentials["email"]

    assert check_code(base_client.get("/users/me/profile/")).get("email-confirmed") is False
    assert check_code(base_client.post(f"/email-confirm/{code}/"))["a"] == "Success"
    assert check_code(base_client.post("/email-confirm/wrong_code/"), 400)["a"] == "Invalid code"
    assert check_code(base_client.get("/users/me/profile/")).get("email-confirmed") is True

    check_code(base_client.post("/signout/"))


@mark.order(13)
def test_password_reset(base_client: FlaskClient, mock_mail):
    link_start, url = "https://xieffect.ru/resetpassword/", "/password-reset/"
    reset_data = (("hey2@hey.hey", True), ("wrong@email.test", False))

    for email, message in reset_data:
        data = {"email": email}
        assert check_code(base_client.post(url, json=data))["a"] is message

    assert len(mock_mail) == 1
    mail_message: Message = mock_mail[0]
    assert mail_message.subject == EmailType.PASSWORD.theme

    code = mail_message.html.partition(link_start)[2].partition('/"')[0]
    wrong_code = EmailType.PASSWORD.generate_code("wrong@email.test")

    confirm_data = (
        (code, "Success"),
        ("Wrong code", "Code error"),
        (wrong_code, "User doesn't exist"),
    )

    for confirm, message in confirm_data:
        pass_data = {"code": confirm, "password": "54321"}
        assert check_code(
            base_client.post(f"{url}confirm/", json=pass_data)
        )["a"] == message


@mark.order(15)
def test_sio_connection(client: FlaskClient):
    sio_client = SocketIOTestClient(client)
    assert sio_client.connected.get("/") is True


@mark.order(16)
def test_sio_unauthorized(base_client: FlaskClient):
    sio_client = SocketIOTestClient(base_client)
    assert sio_client.connected.get("/") is False
