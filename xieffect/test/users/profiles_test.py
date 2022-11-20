from __future__ import annotations

from collections.abc import Callable, Iterator
from json import load as load_json
from pytest import mark

from flask.testing import FlaskClient
from flask_fullstack import check_code

from common import open_file
from ..outside_test import TEST_CREDENTIALS


def test_user_search(list_tester: Callable[[str, dict, int], Iterator[dict]]):
    with open_file("static/test/user-bundle.json") as f:
        usernames = [user_data["username"] for user_data in load_json(f)]
    usernames.extend(["hey_old", "hey"])  # TODO add user deleting & use it in test_signup + remove this line

    for user in list_tester("/users/", {}, 10):
        assert user["username"] != "test"
        assert user["username"] in usernames

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
        "handle": "petrovich",
    }

    check_code(client.post("/settings/", json={"changed": new_settings}))
    data: dict = check_code(client.get("/users/1/profile"))

    for key, value in new_settings.items():
        assert key in data
        assert data[key] == value

    login_id = check_code(client.post("/signin/", json=TEST_CREDENTIALS)).get("id")
    profile_id = check_code(client.get("/users/me/profile/")).get("id")
    for user_id in (login_id, profile_id):
        assert isinstance(user_id, int)
    assert login_id == profile_id


@mark.skip
def test_old_user_profile(client: FlaskClient):  # TODO remove after front update
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
