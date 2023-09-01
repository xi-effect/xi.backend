from __future__ import annotations

from json import load as load_json

from pytest import mark

from common import open_file
from test.conftest import FlaskTestClient


@mark.order(100)
def test_user_search(client: FlaskTestClient):
    with open_file("static/test/user-bundle.json") as f:
        usernames = [user_data["username"] for user_data in load_json(f)]

    for user in client.paginate("/users/"):
        assert user["username"] != "test"
        assert user["username"] in usernames

    for username in usernames[:-1]:
        data: dict = {"search": username[1:-1]}
        for user in client.paginate("/users/", json=data):
            if user["username"] == username:
                break
        else:
            raise AssertionError(f"{username} not found")
