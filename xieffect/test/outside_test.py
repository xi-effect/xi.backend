from __future__ import annotations

from flask_mail import Message
from pydantic import constr
from pytest import mark, param
from pytest_mock import MockerFixture

from other.emailer import EmailType
from test.conftest import (
    BASIC_PASS,
    TEST_EMAIL,
    FlaskTestClient,
    SocketIOTestClient,
    delete_by_id,
)
from users.users_db import User
from wsgi import Invite, TEST_INVITE_ID, socketio

TEST_CREDENTIALS = {"email": TEST_EMAIL, "password": BASIC_PASS}  # noqa: WPS407
BASE_CREDENTIALS = {
    "email": "hey@hey.hey",
    "password": "12345",
    "username": "hey",
    "code": Invite.serializer.dumps((TEST_INVITE_ID, 0)),
}


@mark.order(0)
def test_rest_docs(base_client: FlaskTestClient):
    result = base_client.get("/doc/", get_json=False)
    assert "text/html" in result.content_type


@mark.order(1)
def test_sio_docs(base_client: FlaskTestClient):
    base_client.get("/asyncapi.json", expected_json=socketio.docs())


@mark.order(10)
def test_login(base_client: FlaskTestClient):
    base_client.post(
        "/signin/",
        json=TEST_CREDENTIALS,
        expected_json={"a": "Success", "communities": list, "id": int, "username": str},
        expected_headers={"Set-Cookie": constr(pattern="access_token_cookie=.*")},
    )
    base_client.post("/signout/")


@mark.parametrize(
    ("json", "message"),
    [
        param(
            dict(TEST_CREDENTIALS, email="wrong@user.mail"),
            "User doesn't exist",
            id="email",
        ),
        param(
            dict(TEST_CREDENTIALS, password="wrong_password"),
            "Wrong password",
            id="password",
        ),
    ],
)
def test_login_fails(base_client: FlaskTestClient, json: dict, message: str) -> None:
    base_client.post("/signin/", json=json, expected_a=message)


@mark.parametrize(
    ("code", "status", "message"),
    [
        param("hey", 400, "Malformed code (BadSignature)", id="bad_signature"),
        param(
            Invite.serializer.dumps((-1, 0)), 404, "Invite not found", id="bad_invite"
        ),
    ],
)
def test_signup_fails(
    base_client: FlaskTestClient, mock_mail, code: str, status: int, message: str
):
    base_client.post(
        "/signup/",
        json=dict(BASE_CREDENTIALS, code=code),
        expected_status=status,
        expected_a=message,
    )
    assert len(mock_mail) == 0


@mark.order(15)
def test_signup(base_client: FlaskTestClient, mock_mail):
    # Check successful signup
    result = base_client.post(
        "/signup/",
        json=BASE_CREDENTIALS,
        expected_json={
            "a": "Success",
            "communities": [],
            "username": BASE_CREDENTIALS["username"],
            "id": int,
        },
        expected_headers={"Set-Cookie": constr(pattern="access_token_cookie=.*")},
    )

    # Check the email
    assert len(mock_mail) == 1
    message: Message = mock_mail.pop()
    assert message.subject == EmailType.CONFIRM.theme

    recipients = message.recipients
    assert len(recipients) == 1
    assert recipients[0] == BASE_CREDENTIALS["email"]

    link_start: str = "https://xieffect.ru/email/"
    assert link_start in message.html
    code = message.html.partition(link_start)[2].partition('/"')[0]
    assert code

    # Check email verification
    base_client.get("/users/me/profile/", expected_json={"email-confirmed": False})
    base_client.post(f"/email-confirm/{code}/", expected_a="Success")
    base_client.post(
        "/email-confirm/wrong_code/",
        expected_status=400,
        expected_a="Invalid code",
    )
    base_client.get("/users/me/profile/", expected_json={"email-confirmed": True})

    # Check the /home/ as well
    result.pop("a")
    base_client.get("/home/", expected_json=result)

    # Check email in use error
    base_client.post(
        "/signup/",
        json=BASE_CREDENTIALS,
        expected_a="Email already in use",
    )

    # Clearing database after test
    delete_by_id(result["id"], User)
    assert len(mock_mail) == 0


def test_signup_invites(
    mod_client: FlaskTestClient,
    base_client: FlaskTestClient,
    mock_mail,
):
    # Create a new invite (temp functional)
    invite_id = mod_client.post(
        "/mub/invites/",
        json={"name": "test", "limit": 1},
        expected_json={"id": int},
    )["id"]
    invite_code = Invite.serializer.dumps((invite_id, 0))

    # Checking invite limit exception
    sign_up_data = dict(BASE_CREDENTIALS, email="limit@test.inv", code=invite_code)
    user_id = base_client.post(
        "/signup/",
        json=sign_up_data,
        expected_json={"a": "Success", "id": int},
        expected_headers={"Set-Cookie": constr(pattern="access_token_cookie=.*")},
    )["id"]
    base_client.post(
        "/signup/",
        json=sign_up_data,
        expected_a="Invite code limit exceeded",
        expected_headers={"Set-Cookie": None},
    )
    assert len(mock_mail) == 1

    # Checking invite constraint
    assert (user := User.find_by_id(user_id)) is not None
    assert user.invite_id == invite_id
    delete_by_id(invite_id, Invite)
    assert (user := User.find_by_id(user_id)) is not None
    assert user.invite_id is None

    # Clearing database after test
    delete_by_id(user_id, User)


@mark.order(20)
def test_password_reset(base_client: FlaskTestClient, mock_mail):
    user_id = base_client.post(
        "/signup/",
        json=BASE_CREDENTIALS,
        expected_json={"a": "Success", "id": int},
    )["id"]

    base_client.post(
        "/password-reset/",
        json={"email": BASE_CREDENTIALS.get("email")},
        expected_a=True,
    )
    base_client.post(
        "/password-reset/",
        json={"email": "wrong@email.test"},
        expected_a=False,
    )

    assert len(mock_mail) == 2
    mail_message: Message = mock_mail[-1]
    assert mail_message.subject == EmailType.PASSWORD.theme

    link_start = "https://xieffect.ru/resetpassword/"
    assert link_start in mail_message.html
    code = mail_message.html.partition(link_start)[2].partition('/"')[0]

    base_client.post(
        "password-reset/confirm/",
        json={"code": code, "password": "54321"},
        expected_a="Success",
    )

    # Clearing database after test
    delete_by_id(user_id, User)


@mark.parametrize(
    ("code", "message"),
    [
        param("Wrong code", "Code error", id="wrong_code"),
        param(
            EmailType.PASSWORD.generate_code("wrong@email.test"),
            "User doesn't exist",
            id="bad_email",
        ),
    ],
)
def test_password_reset_fails(base_client: FlaskTestClient, code: str, message: str):
    base_client.post(
        "password-reset/confirm/",
        json={"code": code, "password": "54321"},
        expected_a=message,
    )


@mark.order(30)
def test_sio_connection(client: FlaskTestClient):
    sio_client = SocketIOTestClient(client)
    assert sio_client.connected.get("/") is True


@mark.order(32)
def test_sio_unauthorized(base_client: FlaskTestClient):
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
    client: FlaskTestClient,
    mocker: MockerFixture,
    debug: bool,
    key: str,
    value: bool | None,
    test_user_id: int,
):
    mock = mocker.patch("users.reglog_rst.current_app")
    mock.debug = debug
    client.get("/go/", expected_json={key: test_user_id if value is None else value})
