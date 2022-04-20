from flask.testing import FlaskClient
from pytest import mark

from __lib__.flask_fullstack import check_code


@mark.order(100)
def test_getting_settings(client: FlaskClient):
    data: dict = check_code(client.get("/settings/"))
    for key in ("email", "email-confirmed", "username", "dark-theme", "language"):
        assert key in data.keys()


@mark.order(101)
def test_changing_settings(client: FlaskClient):
    new_settings = {
        "username": "hey",
        "dark-theme": False,
        "avatar": {
            "cool": "avatar",
            "hello": "world",
        },
    }

    old_settings = check_code(client.get("/settings/"))
    assert all(old_settings.get(key, None) != setting for key, setting in new_settings.items())

    check_code(client.post("/settings/", json={"changed": new_settings}))

    result_settings = check_code(client.get("/settings/"))
    for key, setting in new_settings.items():
        assert result_settings[key] == setting, key

    check_code(client.post("/settings/", json={"changed": {
        key: old_settings.get(key, None) for key in new_settings.keys()}}))
    result_settings = check_code(client.get("/settings/"))
    assert all(result_settings[key] == setting for key, setting in old_settings.items())
