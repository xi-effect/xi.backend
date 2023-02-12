from __future__ import annotations

from collections.abc import Callable

from flask.testing import FlaskClient
from flask_fullstack import check_code
from flask_mail import Message
from pytest import mark

from other import EmailType
from vault import File
from wsgi import TEST_EMAIL, BASIC_PASS
from .feedback_test import assert_message
from ..vault_test import upload

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


@mark.order(107)
def test_user_avatar(client: FlaskClient):
    user = check_code(client.get("/users/me/profile/"))
    assert isinstance(user, dict) and isinstance(user.get("id"), int)

    file_id = upload(client, "test-1.json")[0].get("id")
    file = File.find_by_id(file_id)
    assert user.get("id") == file.uploader_id

    data = ((200, True, file_id), (404, "File not found", file_id + 1))
    for code, message, file in data:
        avatar = {"avatar-id": file}
        assert_message(client, "/users/me/avatar/", message, code, **avatar)

    main: dict = check_code(client.get("/home/"))
    assert (main_avatar := main.get("avatar")) is not None
    assert main_avatar.get("id") == file_id

    assert_message(
        client, "/users/me/avatar/", message=True, status=200, method="DELETE"
    )
    assert check_code(client.get("/home/")).get("avatar") is None


@mark.order(108)
def test_changing_pass(client: FlaskClient):
    pass_data = (
        ("WRONG_PASS", "NEW_PASS", "Wrong password"),
        (BASIC_PASS, "NEW_PASS", "Success"),
        ("NEW_PASS", BASIC_PASS, "Success"),
    )
    for password, new_pass, message in pass_data:
        data = {"password": password, "new-password": new_pass}
        assert_message(client, "/users/me/password/", message, **data)


@mark.order(109)
def test_changing_email(client: FlaskClient, mock_mail):
    link_start, new_mail = "https://xieffect.ru/email-change/", "new@test.email"
    email_data = (
        (new_mail, "WRONG_PASS", "Wrong password"),
        (TEST_EMAIL2, BASIC_PASS, "Email in use"),
        (new_mail, BASIC_PASS, "Success"),
    )
    for email, password, message in email_data:
        data = {"new-email": email, "password": password}
        assert_message(client, "/users/me/email/", message, **data)
        if message == "Success":
            assert check_code(client.get("/users/me/profile/")).get("email") == email

    assert len(mock_mail) == 1
    mail_message: Message = mock_mail[0]
    assert mail_message.subject == EmailType.CHANGE.theme

    code = mail_message.html.partition(link_start)[2].partition('/"')[0]
    assert code != ""

    recipients = mail_message.recipients
    assert len(recipients) == 1
    assert recipients[0] == new_mail

    # Reset user's settings
    reset_data = {"new-email": TEST_EMAIL, "password": BASIC_PASS}
    assert_message(client, "/users/me/email/", "Success", **reset_data)
