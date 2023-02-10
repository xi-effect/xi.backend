from __future__ import annotations

from collections.abc import Callable, Iterator
from json import load as load_json

from pytest import mark

from common import open_file


@mark.order(100)
def test_user_search(list_tester: Callable[[str, dict, int], Iterator[dict]]):
    with open_file("static/test/user-bundle.json") as f:
        usernames = [user_data["username"] for user_data in load_json(f)]

    for user in list_tester("/users/", {}, 10):
        assert user["username"] != "test"
        assert user["username"] in usernames

    for username in usernames[:-1]:
        for user in list_tester("/users/", {"search": username[1:-1]}, 10):
            if user["username"] == username:
                break
        else:
            raise AssertionError(f"{username} not found")
