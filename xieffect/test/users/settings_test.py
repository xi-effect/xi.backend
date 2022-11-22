from __future__ import annotations

from flask.testing import FlaskClient
from flask_fullstack import check_code
from pytest import mark


@mark.order(100)
def test_getting_settings(client: FlaskClient):
    data: dict = check_code(client.get("/settings/"))
    for key in ("username", "code"):
        assert key in data


@mark.order(101)
def test_changing_settings(client: FlaskClient):
    new_settings = {
        "username": "hey",
        "handle": "igorthebest",
        "name": "Igor",
        "surname": "Bestov",
        "patronymic": "Thebestovich",
        "birthday": "2011-12-19",
    }

    old_settings = check_code(client.get("/settings/"))
    assert all(old_settings.get(key) != setting for key, setting in new_settings.items())

    check_code(client.post("/settings/", json=new_settings))

    result_settings = check_code(client.get("/settings/"))
    for key, setting in new_settings.items():
        assert result_settings[key] == setting, key

    check_code(client.post("/settings/", json={
        key: old_settings.get(key) for key in new_settings.keys()
    }))
    result_settings = check_code(client.get("/settings/"))
    assert all(result_settings[key] == setting for key, setting in old_settings.items())


@mark.skip
def test_old_getting_settings(client: FlaskClient):  # TODO remove after front update
    data: dict = check_code(client.get("/settings/"))
    for key in ("email", "email-confirmed", "username", "dark-theme", "language"):
        assert key in data


@mark.skip
def test_old_changing_settings(client: FlaskClient):  # TODO remove after front update
    new_settings = {
        "username": "hey",
        "dark-theme": False,
        "avatar": {
            "cool": "avatar",
            "hello": "world",
        },
    }

    old_settings = check_code(client.get("/settings/"))
    assert all(old_settings.get(key) != setting for key, setting in new_settings.items())

    check_code(client.post("/settings/", json={"changed": new_settings}))

    result_settings = check_code(client.get("/settings/"))
    for key, setting in new_settings.items():
        assert result_settings[key] == setting, key

    check_code(client.post("/settings/", json={
        "changed": {
            key: old_settings.get(key) for key in new_settings.keys()
        }
    }))
    result_settings = check_code(client.get("/settings/"))
    assert all(result_settings[key] == setting for key, setting in old_settings.items())
