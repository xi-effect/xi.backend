from flask.testing import FlaskClient
from pytest import mark

from xieffect.test.components import check_status_code


@mark.order(8)
def test_missing_url(client: FlaskClient):
    check_status_code(client.get("/this-does-not-exist"), 404)


@mark.order(9)
def test_missing_module(client: FlaskClient):
    check_status_code(client.post("/modules/-1/report/", json={"reason": "It's so negative!"}), 404)
