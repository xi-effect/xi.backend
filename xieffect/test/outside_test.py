from __future__ import annotations

from flask.testing import FlaskClient
from flask_fullstack import check_code, dict_equal
from flask_mail import Message
from pytest import mark
from pytest_mock import MockerFixture
from werkzeug.test import TestResponse

from common import User
from communities import CommunitiesUser
from other import EmailType
from test.conftest import BASIC_PASS, TEST_EMAIL, SocketIOTestClient, delete_by_id
from wsgi import Invite, TEST_INVITE_ID, socketio

TEST_CREDENTIALS = {"email": TEST_EMAIL, "password": BASIC_PASS}  # noqa: WPS407
BASE_CREDENTIALS = {
    "email": "hey@hey.hey",
    "password": "12345",
    "username": "hey",
    "code": Invite.serializer.dumps((TEST_INVITE_ID, 0)),
}


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

    # Checking fails
    credentials = (
        (dict(TEST_CREDENTIALS, password="wrong_password"), "Wrong password"),
        (dict(TEST_CREDENTIALS, email="wrong@user.mail"), "User doesn't exist"),
    )
    for data, message in credentials:
        assert check_code(base_client.post("/signin/", json=data))["a"] == message

    check_code(base_client.post("/signout/"))


@mark.order(11)
def test_signup(
    mod_client: FlaskClient,
    base_client: FlaskClient,
    mock_mail,
):
    user_collection = list()

    def assert_with_code(code: str, status: int, message: str):
        assert check_code(
            base_client.post("/signup/", json=dict(BASE_CREDENTIALS, code=code)), status
        )["a"] == message

    # Checking fails
    assert_with_code("hey", 400, "Malformed code (BadSignature)")
    assert_with_code(Invite.serializer.dumps((-1, 0)), 404, "Invite not found")
    assert len(mock_mail) == 0

    invite_data = {"name": "test", "limit": 1}
    invite_id = check_code(mod_client.post("/mub/invites/", json=invite_data)).get("id")
    assert isinstance(invite_id, int)

    # Checking invite limit exception
    invite_code = Invite.serializer.dumps((invite_id, 0))
    sign_up_data = dict(BASE_CREDENTIALS, email="limit@test.inv", code=invite_code)
    for a_message in ("Success", "Invite code limit exceeded"):
        response = check_code(base_client.post("/signup/", json=sign_up_data))
        assert response["a"] == a_message

        if a_message == "Success":
            user_collection.append(response.get("id"))

    # Checking invite constraint
    assert (user := User.find_by_id(user_collection[-1])) is not None
    assert user.invite_id == invite_id
    delete_by_id(invite_id, Invite)
    assert (user := User.find_by_id(user_collection[-1])) is not None
    assert user.invite_id is None

    # Checking successful sing up
    response = check_code(base_client.post("/signup/", json=BASE_CREDENTIALS), get_json=False)
    assert_with_code(Invite.serializer.dumps((TEST_INVITE_ID, 0)), 200, "Email already in use")
    assert len(mock_mail) == 2

    # Checking the returned data
    result: dict[str, ...] = response.json
    assert result.pop("a", None) == "Success"

    communities = result.get("communities")
    assert isinstance(communities, list)
    assert len(communities) == 0

    assert isinstance(result, dict)
    assert dict_equal(result, BASE_CREDENTIALS, "username")
    assert isinstance(result.get("id"), int)
    user_collection.append(result.get("id"))

    # Checking for cookies
    assert "Set-Cookie" in response.headers
    cookie: tuple[str, str] = response.headers["Set-Cookie"].partition("=")[::2]
    assert cookie[0] == "access_token_cookie"

    # Check the /home/ as well
    response = check_code(base_client.get("/home/"))
    assert response == result

    check_code(base_client.post("/signout/"))

    # Clearing database after test
    for user_id in user_collection:
        delete_by_id(user_id, User)
        assert CommunitiesUser.find_by_id(user_id) is None


@mark.order(12)
def test_email_confirm(base_client: FlaskClient, mock_mail):
    link_start = "https://xieffect.ru/email/"

    response = check_code(base_client.post("/signup/", json=BASE_CREDENTIALS))
    assert response["a"] == "Success"
    assert isinstance(response.get("id"), int)

    assert len(mock_mail) == 1
    message: Message = mock_mail[0]
    assert message.subject == EmailType.CONFIRM.theme
    assert link_start in message.html

    code = message.html.partition(link_start)[2].partition('/"')[0]
    assert code != ""

    recipients = message.recipients
    assert len(recipients) == 1
    assert recipients[0] == BASE_CREDENTIALS["email"]

    assert check_code(base_client.get("/users/me/profile/")).get("email-confirmed") is False
    assert check_code(base_client.post(f"/email-confirm/{code}/"))["a"] == "Success"
    assert check_code(base_client.post("/email-confirm/wrong_code/"), 400)["a"] == "Invalid code"
    assert check_code(base_client.get("/users/me/profile/")).get("email-confirmed") is True

    check_code(base_client.post("/signout/"))

    delete_by_id(response.get("id"), User)


@mark.order(13)
def test_password_reset(base_client: FlaskClient, mock_mail):
    link_start, url = "https://xieffect.ru/resetpassword/", "/password-reset/"

    response = check_code(base_client.post("/signup/", json=BASE_CREDENTIALS))
    assert response["a"] == "Success"
    assert isinstance(response.get("id"), int)

    reset_data = ((BASE_CREDENTIALS.get("email"), True), ("wrong@email.test", False))
    for email, message in reset_data:
        data = {"email": email}
        assert check_code(base_client.post(url, json=data))["a"] is message

    assert len(mock_mail) == 2
    mail_message: Message = mock_mail[-1]
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

    check_code(base_client.post("/signout/"))

    delete_by_id(response.get("id"), User)


@mark.order(15)
def test_sio_connection(client: FlaskClient):
    sio_client = SocketIOTestClient(client)
    assert sio_client.connected.get("/") is True


@mark.order(16)
def test_sio_unauthorized(base_client: FlaskClient):
    sio_client = SocketIOTestClient(base_client)
    assert sio_client.connected.get("/") is False


@mark.parametrize(
    ("debug", "key", "value"),
    [
        (True, "id", None),
        (False, "a", False),
    ],
    ids=["debug", "production"],
)
def test_go(
    client: FlaskClient,
    mocker: MockerFixture,
    debug: bool,
    key: str,
    value: bool | None,
    test_user_id: int,
):
    mock = mocker.patch("users.reglog_rst.current_app")
    mock.debug = debug
    response = check_code(client.get("/go/"))
    assert response.get(key) == (test_user_id if value is None else value)
