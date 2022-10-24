from __future__ import annotations

from pytest import skip
from flask.testing import FlaskClient
from flask_fullstack import dict_equal, check_code
from flask_mail import Message

from common import mail, mail_initialized
from other import EmailType
from wsgi import Invite


def assert_error(
    client,
    url: str,
    status: int,
    message: str,
    method="POST",
    **kwargs,
):
    assert check_code(
        client.open(url, json=kwargs, method=method), status
    )["a"] == message


def test_mub_users(
    client: FlaskClient,
    mod_client: FlaskClient,
    list_tester,
):
    # Check getting list of users
    url, base_status, base_message = "/mub/users/", 403, "Permission denied"
    user_list = list(list_tester(url, {}, 50, use_post=False))
    counter = len(user_list)
    cli_data = {"counter": 50, "offset": 0}
    assert_error(client, url, base_status, base_message, method="GET", **cli_data)

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
    cli_data = dict(user_data, email="fo@test.mub")
    assert_error(client, url, base_status, base_message, **cli_data)
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


def test_mub_emailer(
    client: FlaskClient,
    mod_client: FlaskClient,
    list_tester,
):
    if not mail_initialized:
        skip("Email module is not setup")

    email_user = list(list_tester("/mub/users/", {}, 50, use_post=False))[-1]["email"]

    with mail.record_messages() as outbox:
        url, user, tester = "/mub/emailer/send/", email_user, "test@test.test"
        emailer_data = [
            ("confirm", "wrong@mail.it", 404, "User not found"),
            ("confirm", None, 200, None),
            ("change", user, 200, None),
            ("password", user, 200, None),
        ]
        counter = 0

        for e_type, email, status, message in emailer_data:
            data = {"type": e_type, "user-email": email, "tester-email": tester}

            # Check successful sending
            if message is None:
                mailer = check_code(mod_client.post(url, json=data))
                email_type = EmailType.from_string(data["type"])
                counter += 1

                assert len(mailer.get("a")) != 0
                assert mail_initialized is not None
                assert len(outbox) == counter

                mail_message: Message = outbox[counter-1]
                assert mail_message.subject == email_type.theme

                recipients = mail_message.recipients
                assert len(recipients) == 1
                assert recipients[0] == tester

                # Check base-client exception
                assert_error(client, url, 403, "Permission denied", **data)
            else:
                # Check moderators exception
                assert_error(mod_client, url, status, message, **data)
