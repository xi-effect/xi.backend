from __future__ import annotations

from collections.abc import Callable
from flask.testing import FlaskClient
from flask_fullstack import check_code
from flask_mail import Message
from pytest import mark, skip

from common import mail, mail_initialized
from .feedback_test import assert_message
from other import EmailType
from vault import File
from ..vault_test import upload
from wsgi import TEST_EMAIL, BASIC_PASS

TEST_EMAIL2 = "2@user.user"


@mark.order(106)
def test_changing_settings(
    client: FlaskClient, multi_client: Callable[[str], FlaskClient]
):

    # Check getting settings
    old_settings: dict = check_code(client.get("/users/me/profile/"))
    for key in ("email", "email-confirmed", "username", "code"):
        assert key in old_settings

    new_settings = {
        "username": "hey",
        "handle": "igorthebest",
        "name": "Igor",
        "surname": "Bestov",
        "patronymic": "Thebestovich",
        "birthday": "2011-12-19",
    }
    assert all(
        old_settings.get(key) != setting for key, setting in new_settings.items()
    )

    # Check changing settings
    check_code(client.post("/users/me/profile/", json=new_settings))
    result_settings = check_code(client.get("/users/me/profile/"))
    for key, setting in new_settings.items():
        assert result_settings[key] == setting, key

    # Check handle error
    client2 = multi_client(TEST_EMAIL2)
    assert_message(
        client2,
        "/users/me/profile/",
        "Handle already in use",
        handle=new_settings["handle"],
    )

    check_code(
        client.post(
            "/users/me/profile/",
            json={key: old_settings.get(key) for key in new_settings.keys()},
        )
    )
    result_settings = check_code(client.get("/users/me/profile/"))
    assert all(result_settings[key] == setting for key, setting in old_settings.items())

    # Check changing password
    data = (
        ("WRONGPASS", "NEW_PASS", "Wrong password"),
        (BASIC_PASS, "NEW_PASS", "Success"),
        ("NEW_PASS", BASIC_PASS, "Success"),
    )
    for password, new_pass, message in data:
        pass_data = {"password": password, "new-password": new_pass}
        assert_message(client, "/users/me/password/", message, **pass_data)


@mark.order(107)
def test_user_avatar(client: FlaskClient, multi_client: Callable[[str], FlaskClient]):
    client2 = multi_client(TEST_EMAIL2)
    user, user2 = [
        check_code(key.get("/users/me/profile/")) for key in (client, client2)
    ]
    for result in (user, user2):
        assert isinstance(result, dict)
        assert isinstance(result.get("id"), int)

    file_id = upload(client, "sample-page.json")[0].get("id")
    file = File.find_by_id(file_id)
    assert user.get("id") == file.uploader_id
    assert user2.get("id") != file.uploader_id

    data = ((client, 200, True), (client2, 404, "File doesn't exist"))
    avatar = {"avatar-id": file_id}
    for user, code, message in data:
        assert_message(user, "/users/me/avatar/", message, code, **avatar)

    main: dict = check_code(client.get("/main/"))
    assert (main_avatar := main.get("avatar")) is not None
    assert main_avatar.get("id") == file_id

    assert_message(
        client, "/users/me/avatar/", message=True, status=200, method="DELETE"
    )
    assert check_code(client.get("/main/")).get("avatar") is None


@mark.order(108)
def test_changing_email(client: FlaskClient):
    if not mail_initialized:  # TODO pragma: no coverage
        skip("Email module is not setup")

    with mail.record_messages() as outbox:
        data = (
            ("new@test.email", "WRONGPASS", "Wrong password"),
            (TEST_EMAIL2, BASIC_PASS, "Email in use"),
            ("new@test.email", BASIC_PASS, None),
            (TEST_EMAIL, BASIC_PASS, None),
        )
        counter = 0

        for email, password, message in data:
            url, data = "/users/me/email/", {"new-email": email, "password": password}

            if message is None:
                mailer = check_code(client.post(url, json=data))
                email_type = EmailType.CHANGE
                counter += 1

                assert len(mailer.get("a")) != 0
                assert mail_initialized is not None
                assert len(outbox) == counter

                mail_message: Message = outbox[counter - 1]
                assert mail_message.subject == email_type.theme

                recipients = mail_message.recipients
                assert len(recipients) == 1
                assert recipients[0] == email
            else:
                assert_message(client, url, message, **data)
