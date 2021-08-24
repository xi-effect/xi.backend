from pytest import mark
from flask.testing import FlaskClient
from flask.wrappers import Response


@mark.order(3)
def test_getting_settings(client: FlaskClient):
    response: Response = client.get("/settings", follow_redirects=True)
    assert response.status_code == 200
    data: dict = response.get_json()
    assert all(key in data.keys()
               for key in ("email", "email-confirmed", "username", "name", "surname",
                           "patronymic", "dark-theme", "language"))


@mark.order(4)
def test_changing_settings(client: FlaskClient):
    pass
