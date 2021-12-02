from json import load
from random import choice
from typing import Iterator, Callable

from flask.testing import FlaskClient

from .components import check_status_code


def test_user_search(client: FlaskClient, list_tester: Callable[[str, dict, int], Iterator[dict]]):
    with open("../files/test/user-bundle.json", encoding="utf-8") as f:
        usernames = [user_data["username"] for user_data in load(f)]
    usernames.append("hey")  # TODO Add user deleting & use it in test_signup + remove this line

    admin_user_found = False
    for user in list_tester("/users/", {}, 10):
        assert user["username"] != "test"
        if user["username"] == "admin":
            admin_user_found = True
        else:
            assert user["username"] in usernames
    assert admin_user_found

    some_name = choice(usernames)
    assert any(user["username"] == some_name for user in list_tester("/users/", {"search": some_name[1:-1]}, 10))


def test_user_profile(client: FlaskClient):
    new_settings: dict[str, str] = {
        "name": "Danila",
        "surname": "Petrov",
        "patronymic": "Danilovich",
        "bio": "Pricol",
        "group": "3B"
    }

    check_status_code(client.post("/settings/", json={"changed": new_settings}))
    data: dict = check_status_code(client.get("/users/1/profile"))

    for key, value in new_settings.items():
        assert key in data.keys()
        assert data[key] == value
