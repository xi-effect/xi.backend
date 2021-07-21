from flask import Response
from flask.testing import FlaskClient


def test_module_list(client: FlaskClient):
    counter = 0
    amount = 12
    while amount == 12:
        response: Response = client.post("/modules", data={"counter": counter}, follow_redirects=True)
        assert response.status_code == 200
        amount = len(response.get_json())
        assert amount < 13
        counter += 1
    assert counter > 0
