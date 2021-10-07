from flask.testing import FlaskClient
from pytest import mark

from xieffect.test.components import check_status_code


@mark.order(100)
def test_getting_settings(client: FlaskClient):
    data: dict = check_status_code(client.get("/settings", follow_redirects=True))
    for key in ("email", "email-confirmed", "username", "dark-theme", "language"):
        assert key in data.keys()


@mark.order(101)
def test_changing_settings(client: FlaskClient):
    pass
