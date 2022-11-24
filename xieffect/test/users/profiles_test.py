from __future__ import annotations

from collections.abc import Callable, Iterator
from json import load as load_json
from pytest import mark

from flask.testing import FlaskClient
from flask_fullstack import check_code

from common import open_file


@mark.order(100)
def test_user_search(list_tester: Callable[[str, dict, int], Iterator[dict]]):
    with open_file("static/test/user-bundle.json") as f:
        usernames = [user_data["username"] for user_data in load_json(f)]
    usernames.append("hey")  # TODO add user deleting & use it in test_signup + remove this line

    for user in list_tester("/users/", {}, 10):
        assert user["username"] != "test"
        assert user["username"] in usernames

    for username in usernames[:-1]:
        for user in list_tester("/users/", {"search": username[1:-1]}, 10):
            if user["username"] == username:
                break
        else:
            raise AssertionError(f"{username} not found")


@mark.order(101)
def test_user_profile(client: FlaskClient, test_user_id: int):
    new_settings: dict[str, str] = {
        "name": "Danila",
        "surname": "Petrov",
        "patronymic": "Danilovich",
        "handle": "petrovich",
    }

    check_code(client.post("/users/me/profile/", json=new_settings))
    data: dict = check_code(client.get(f"/users/{test_user_id}/profile"))

    for key, value in new_settings.items():
        assert key in data
        assert data[key] == value
