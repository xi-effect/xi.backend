from typing import Iterator, Callable

from flask.testing import FlaskClient

from .components import check_status_code


def test_user_search(client: FlaskClient, list_tester: Callable[[str, dict, int], Iterator[dict]]):
    results = list(list_tester("/users/", {}, 10))

    for res in results:
        assert res["username"] != "test"
        if res["username"] == "admin":
            break
    else:
        assert False, "Admin user not found"


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
