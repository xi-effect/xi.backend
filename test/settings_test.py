from flask.testing import FlaskClient
from flask.wrappers import Response


def test_getting_settings(client: FlaskClient):
    response: Response = client.get("/settings", follow_redirects=True)
    assert response.status_code == 200
    data: dict = response.get_json()
    assert all(key in data.keys()
               for key in ("email", "email-confirmed", "username", "name", "surname",
                           "patronymic", "dark-theme", "language"))


def test_changing_settings(client: FlaskClient):
    pass
