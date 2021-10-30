from flask.testing import FlaskClient

from .components import check_status_code


def test_profiles_user(client: FlaskClient, ):
    check_status_code(client.post("/settings/", json={"changed": {"name": "Danila", "surname": "Petrov",
                                                                  "patronymic": "Danilovich", "bio": "Pricol",
                                                                  "group": "3B"}}))

    data: dict = check_status_code(client.get("/users/1/profile"))

    assert "name" in data.keys()
    assert data["name"] == "Danila"

    assert "surname" in data.keys()
    assert data["surname"] == "Petrov"

    assert "patronymic" in data.keys()
    assert data["patronymic"] == "Danilovich"

    assert "bio" in data.keys()
    assert data["bio"] == "Pricol"

    assert "group" in data.keys()
    assert data["group"] == "3B"
