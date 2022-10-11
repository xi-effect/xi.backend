from __future__ import annotations

from collections.abc import Callable, Iterator
from json import load as load_json

from flask.testing import FlaskClient
from flask_fullstack import check_code


def test_user_search(list_tester: Callable[[str, dict, int], Iterator[dict]]):
    with open("../static/test/user-bundle.json", encoding="utf-8") as f:
        usernames = [user_data["username"] for user_data in load_json(f)]
    usernames.append("hey")  # TODO add user deleting & use it in test_signup + remove this line

    admin_user_found = False
    for user in list_tester("/users/", {}, 10):
        assert user["username"] != "test"
        if user["username"] == "admin":
            admin_user_found = True
        else:
            assert user["username"] in usernames
    assert admin_user_found

    for username in usernames[:-1]:
        for user in list_tester("/users/", {"search": username[1:-1]}, 10):
            if user["username"] == username:
                break
        else:
            raise AssertionError(f"{username} not found")


def test_user_profile(client: FlaskClient):
    new_settings: dict[str, str] = {
        "name": "Danila",
        "surname": "Petrov",
        "patronymic": "Danilovich",
        "bio": "Pricol",
        "group": "3B"
    }

    check_code(client.post("/settings/", json={"changed": new_settings}))
    data: dict = check_code(client.get("/users/1/profile"))

    for key, value in new_settings.items():
        assert key in data
        assert data[key] == value
