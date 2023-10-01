from __future__ import annotations

from random import choice
from smtplib import SMTPDataError

from flask_mail import Message
from pytest import mark, param
from pytest_mock import MockerFixture

from common import TEST_EMAIL
from other.emailer import EmailType, WebhookURLs
from test.conftest import FlaskTestClient, delete_by_id
from users.users_db import User
from wsgi import Invite


@mark.parametrize(
    ("email", "code", "status", "message"),
    [
        param(TEST_EMAIL, None, 200, "Email already in use", id="email_in_use"),
        param(
            "new@new.new",
            "wrong.code",
            400,
            "Malformed code (BadSignature)",
            id="bad_code",
        ),
        param(
            "new@new.new",
            Invite.serializer.dumps((-1, 0)),
            404,
            "Invite not found",
            id="bad_invite",
        ),
    ],
)
def test_mub_user_creation_fails(
    mod_client: FlaskTestClient,
    email: str,
    code: str | None,
    status: int,
    message: str,
):
    mod_client.post(
        "/mub/users/",
        json={"username": "mub", "password": "123456", "code": code, "email": email},
        expected_status=status,
        expected_a=message,
    )


def test_mub_users(mod_client: FlaskTestClient):
    # Check getting list of users
    base_url = "/mub/users/"
    counter = len(list(mod_client.paginate(base_url)))

    # Check creating
    public_data = {"username": "mub", "email": "fi@test.mub"}
    data = dict(public_data, password="123456")
    new_user = mod_client.post(base_url, json=data, expected_json=public_data)
    assert counter + 1 == len(list(mod_client.paginate(base_url)))

    # Checking invite limit exception
    invite_data = {"name": "test", "limit": 1}
    invite_id: int = mod_client.post(
        "/mub/invites/", json=invite_data, expected_json={"id": int}
    )["id"]

    code = Invite.serializer.dumps((invite_id, 0))
    credentials = dict(data, email="limit@invite.mub", code=code)
    for message in (None, "Invite code limit exceeded"):
        mod_client.post(base_url, expected_a=message, json=credentials)

    # Check email-confirmed update
    resp = list(mod_client.paginate(base_url, json={"username": new_user["username"]}))
    assert len(resp) > 1
    old_data = resp[0]
    assert isinstance(old_data, dict)

    old_data.pop("email")
    url = f"{base_url}{new_user['id']}/"
    for confirmed in (True, False):
        new_data = {"email-confirmed": confirmed}
        mod_client.put(
            url,
            json=new_data,
            expected_json=dict(old_data, **new_data),
        )

    delete_by_id(new_user["id"], User)


@mark.parametrize(
    "email_type",
    [param(member, id=member.to_string()) for member in EmailType.__members__.values()],
)
@mark.parametrize(
    ("user_email", "status", "message"),
    [
        param(None, 200, None, id="tester-user"),
        param("1@user.user", 200, None, id="other-user"),
        param("wrong@mail.it", 404, "User not found", id="not-existing-user"),
    ],
)
def test_mub_emailer(
    mod_client: FlaskTestClient,
    email_type: EmailType,
    user_email: str | None,
    status: int,
    message: str | None,
    mock_mail,
):
    url = "/mub/emailer/send/"
    tester_email = "test@test.test"
    data = {
        "type": email_type.to_string(),
        "user-email": user_email,
        "tester-email": tester_email,
    }

    if status == 200:  # Check successful sending
        mod_client.post(url, json=data, expected_a=str)

        assert len(mock_mail) == 1
        mail_message: Message = mock_mail[0]
        assert mail_message.subject == email_type.theme

        recipients = mail_message.recipients
        assert len(recipients) == 1
        assert recipients[0] == tester_email
    else:
        mod_client.post(url, expected_status=status, expected_a=message, json=data)


def test_smtp_data_error(mod_client: FlaskTestClient, mocker: MockerFixture, mock_mail):
    data = {
        "type": choice(EmailType.get_all_field_names()),
        "tester-email": "test@test.test",
    }
    mocker.patch(
        "common._core.mail.send",
        side_effect=SMTPDataError(554, "No SMTP service here"),
    )
    mock_discorder = mocker.patch("other.emailer.send_discord_message")
    mock_discorder.side_effect = lambda *_: None

    mod_client.post("/mub/emailer/send/", json=data)
    assert len(mock_mail) == 0

    message = "Email for test@test.test not sent:\n```(554, 'No SMTP service here')```"
    mock_discorder.assert_called_with(WebhookURLs.MAILBT, message)
