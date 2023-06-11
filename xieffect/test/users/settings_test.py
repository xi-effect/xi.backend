from __future__ import annotations

from collections.abc import Callable

from flask_mail import Message
from pytest import mark, param

from other import EmailType
from test.conftest import FlaskTestClient
from test.vault_test import upload
from vault import File
from wsgi import TEST_EMAIL, BASIC_PASS

TEST_EMAIL2 = "2@user.user"


@mark.order(106)
def test_changing_settings(
    client: FlaskTestClient,
    multi_client: Callable[[str], FlaskTestClient],
    test_user_id: int,
):
    client2 = multi_client(TEST_EMAIL2)

    # Check getting settings
    settings_model: dict = {
        "handle": None,
        "email": str,
        "email-confirmed": bool,
        "username": str,
        "code": str,
    }
    old_settings = client.get("/users/me/profile/", expected_json=settings_model)
    client2.get(f"/users/{test_user_id}/profile/", expected_json=old_settings)

    # Check changing settings
    new_settings = {
        "username": "hey",
        "name": "Igor",
        "surname": "Bestov",
        "patronymic": "Thebestovich",
        "birthday": "2011-12-19",
        "theme": "blue",
    }
    assert all(
        old_settings.get(key) != setting for key, setting in new_settings.items()
    )

    client.post("/users/me/profile/", json=new_settings)
    client.get("/users/me/profile/", expected_json=new_settings)
    client2.get(f"/users/{test_user_id}/profile/", expected_json=new_settings)

    # Check handle error
    handle: str = "igor_the_best"
    client.post("/users/me/profile/", json={"handle": handle})
    client.get("/users/me/profile/", expected_json=dict(new_settings, handle=handle))

    client2.post(
        "/users/me/profile/",
        json={"handle": handle},
        expected_a="Handle already in use",
    )

    client.post("/users/me/profile/", json=old_settings)
    client.get("/users/me/profile/", expected_json=old_settings)


@mark.order(107)
def test_user_avatar(client: FlaskTestClient):
    user = client.get("/users/me/profile/", expected_json={"id": int})

    file_id = upload(client, "test-1.json")[0].get("id")
    file = File.find_by_id(file_id)
    assert user.get("id") == file.uploader_id

    data = ((200, True, file_id), (404, "File not found", file_id + 1))
    for code, message, file in data:
        avatar = {"avatar-id": file}
        client.post(
            "/users/me/avatar/", expected_a=message, expected_status=code, json=avatar
        )

    client.get("/home/", expected_json={"avatar": {"id": file_id}})

    client.delete("/users/me/avatar/", expected_a=True)
    client.get("/home/", expected_json={"avatar": None})


@mark.parametrize(
    ("password", "new_password", "message"),
    [
        param("WRONG_PASS", "NEW_PASS", "Wrong password", id="wrong_password"),
        param(BASIC_PASS, "NEW_PASS", "Success", id="success"),
    ],
)
def test_changing_pass(
    fresh_client: FlaskTestClient, password: str, new_password: str, message: str
):
    data = {"password": password, "new-password": new_password}
    fresh_client.post("/users/me/password/", expected_a=message, json=data)


@mark.parametrize(
    ("email", "password", "message"),
    [
        param("new@test.email", "WRONG_PASS", "Wrong password", id="wrond_password"),
        param(TEST_EMAIL2, BASIC_PASS, "Email in use", id="email_in_use"),
    ],
)
def test_changing_email_fails(
    client: FlaskTestClient, mock_mail, email: str, password: str, message: str
):
    data = {"new-email": email, "password": password}
    client.post("/users/me/email/", expected_a=message, json=data)
    assert len(mock_mail) == 0


@mark.order(109)
def test_changing_email(client: FlaskTestClient, mock_mail):
    new_mail: str = "new@test.email"

    data = {"new-email": new_mail, "password": BASIC_PASS}
    client.post("/users/me/email/", expected_a="Success", json=data)
    client.get("/users/me/profile/", expected_json={"email": new_mail})

    assert len(mock_mail) == 1
    mail_message: Message = mock_mail[0]
    assert mail_message.subject == EmailType.CHANGE.theme

    link_start: str = "https://xieffect.ru/email-change/"
    assert link_start in mail_message.html
    code = mail_message.html.partition(link_start)[2].partition('/"')[0]
    assert code != ""

    recipients = mail_message.recipients
    assert len(recipients) == 1
    assert recipients[0] == new_mail

    # Reset user's settings
    reset_data = {"new-email": TEST_EMAIL, "password": BASIC_PASS}
    client.post("/users/me/email/", expected_a="Success", json=reset_data)
