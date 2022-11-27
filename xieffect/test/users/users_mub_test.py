from __future__ import annotations

from flask.testing import FlaskClient
from flask_fullstack import dict_equal, check_code
from flask_mail import Message
from pytest import skip, mark, param

from common import mail, mail_initialized
from other import EmailType
from wsgi import Invite


def assert_error(
    client,
    url: str,
    status: int,
    message: str,
    method: str = "POST",
    **kwargs,
) -> None:
    response = check_code(client.open(url, json=kwargs, method=method), status)
    assert response.get("a", None) == message


def test_mub_users(client: FlaskClient, mod_client: FlaskClient, list_tester):
    # Check getting list of users
    url, base_status, base_message = "/mub/users/", 403, "Permission denied"
    counter = len(list(list_tester(url, {}, 50, use_post=False)))
    assert_error(client, url, base_status, base_message, method="GET", offset=0)

    # Check creating
    invite_code = Invite.serializer.dumps((-1, 0))
    create_data = [
        ("fi", None, 200, None),
        ("fi", None, 200, "Email already in use"),
        ("se", "wrong.code", 400, "Malformed code (BadSignature)"),
        ("tr", invite_code, 404, "Invite not found"),
    ]
    user_data = {"username": "mub", "password": "123456"}
    for i, code, status, message in create_data:
        data = dict(user_data, code=code, email=f"{i}@test.mub")
        if message is None:
            new_user = check_code(mod_client.post(url, json=data))
            assert dict_equal(new_user, data, "username", "email")
            counter += 1
        else:
            assert_error(mod_client, url, status, message, **data)
    base_data = dict(user_data, email="fo@test.mub")
    assert_error(client, url, base_status, base_message, **base_data)
    assert counter == len(list(list_tester("/mub/users/", {}, 50, use_post=False)))

    # Check email-confirmed update
    old_date = list(
        list_tester(url, {"username": new_user["username"]}, 50, use_post=False)
    )
    url = f"/mub/users/{new_user['id']}/"
    for conf in (True, False):
        result = check_code(mod_client.put(url, json={"email-confirmed": conf}))
        assert isinstance(old_date[0], dict)
        assert old_date[0].get("id") == new_user["id"]
        assert result.get("email-confirmed") == conf
        assert dict_equal(result, old_date[0], "id", "username", "email", "code")
    base_data = {"email-confirmed": True}
    assert_error(client, url, base_status, base_message, method="PUT", **base_data)


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
    mod_client: FlaskClient,
    email_type: EmailType,
    user_email: str | None,
    status: int,
    message: str | None,
):  # TODO pragma: no coverage (action)
    if not mail_initialized:  # TODO pragma: no coverage
        skip("Email module is not setup")

    url = "/mub/emailer/send/"
    tester_email = "test@test.test"

    with mail.record_messages() as outbox:
        data = {
            "type": email_type.to_string(),
            "user-email": user_email,
            "tester-email": tester_email
        }

        if status == 200:  # Check successful sending
            response = check_code(mod_client.post(url, json=data))
            assert isinstance(response.get("a"), str)

            assert len(outbox) == 1
            mail_message: Message = outbox[0]
            assert mail_message.subject == email_type.theme

            recipients = mail_message.recipients
            assert len(recipients) == 1
            assert recipients[0] == tester_email
        else:
            assert_error(mod_client, url, status, message, **data)
