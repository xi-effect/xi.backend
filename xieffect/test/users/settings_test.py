from __future__ import annotations

from collections.abc import Callable

from flask.testing import FlaskClient
from flask_fullstack import check_code, dict_equal
from pytest import mark

from vault import File
from wsgi import TEST_EMAIL, BASIC_PASS
from .feedback_test import assert_message
from ..vault_test import upload

TEST_EMAIL2 = "2@user.user"


@mark.order(106)
def test_changing_settings(
    client: FlaskClient,
    multi_client: Callable[[str], FlaskClient],
    test_user_id: int,
):
    client2 = multi_client(TEST_EMAIL2)

    # Check getting settings
    old_settings: dict = check_code(client.get("/users/me/profile/"))
    assert old_settings.get("handle") is None
    for key in ("email", "email-confirmed", "username", "code"):
        assert key in old_settings

    public_profile = check_code(client2.get(f"/users/{test_user_id}/profile/"))
    assert dict_equal(public_profile, old_settings, *public_profile.keys())

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

    check_code(client.post("/users/me/profile/", json=new_settings))
    result_settings = check_code(client.get("/users/me/profile/"))
    for key, setting in new_settings.items():
        assert result_settings[key] == setting, key

    public_profile = check_code(client2.get(f"/users/{test_user_id}/profile/"))
    assert dict_equal(public_profile, result_settings, *public_profile.keys())

    # Check handle error
    handle: str = "igor_the_best"
    check_code(client.post("/users/me/profile/", json={"handle": handle}))
    result_settings = check_code(client.get("/users/me/profile/"))
    for key, setting in new_settings.items():
        assert result_settings[key] == setting, key
    assert result_settings["handle"] == handle

    assert_message(
        client2,
        "/users/me/profile/",
        "Handle already in use",
        handle=handle,
    )

    check_code(client.post("/users/me/profile/", json=old_settings))
    result_settings = check_code(client.get("/users/me/profile/"))
    assert all(result_settings[key] == setting for key, setting in old_settings.items())


@mark.order(107)
def test_user_avatar(client: FlaskClient):
    user = check_code(client.get("/users/me/profile/"))
    assert isinstance(user, dict) and isinstance(user.get("id"), int)

    file_id = upload(client, "sample-page.json")[0].get("id")
    file = File.find_by_id(file_id)
    assert user.get("id") == file.uploader_id

    data = ((200, True, file_id), (404, "File not found", file_id + 1))
    for code, message, file in data:
        avatar = {"avatar-id": file}
        assert_message(client, "/users/me/avatar/", message, code, **avatar)

    main: dict = check_code(client.get("/home/"))
    assert (main_avatar := main.get("avatar")) is not None
    assert main_avatar.get("id") == file_id

    assert_message(client, "/users/me/avatar/", message=True, method="DELETE")
    assert check_code(client.get("/home/")).get("avatar") is None


@mark.order(108)
def test_changing_pass(client: FlaskClient):
    pass_data = (
        ("WRONGPASS", "NEW_PASS", "Wrong password"),
        (BASIC_PASS, "NEW_PASS", "Success"),
        ("NEW_PASS", BASIC_PASS, "Success"),
    )
    for password, new_pass, message in pass_data:
        data = {"password": password, "new-password": new_pass}
        assert_message(client, "/users/me/password/", message, **data)


@mark.order(109)
def test_error_email(client: FlaskClient):
    email_data = (
        ("new@test.email", "WRONGPASS", "Wrong password"),
        (TEST_EMAIL2, BASIC_PASS, "Email in use"),
        ("new@test.email", BASIC_PASS, "Success"),
        (TEST_EMAIL, BASIC_PASS, "Success"),
    )
    for email, password, message in email_data:
        data = {"new-email": email, "password": password}
        assert_message(client, "/users/me/email/", message, **data)
