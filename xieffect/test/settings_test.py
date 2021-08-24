from flask.testing import FlaskClient
from pytest import mark

from xieffect.test.components import check_status_code


@mark.order(3)
def test_getting_settings(client: FlaskClient):
    data: dict = check_status_code(client.get("/settings", follow_redirects=True))
    assert all(key in data.keys()
               for key in ("email", "email-confirmed", "username", "name", "surname",
                           "patronymic", "dark-theme", "language"))


@mark.order(4)
def test_changing_settings(client: FlaskClient):
    pass
