from typing import Iterator

from flask import Response
from flask.testing import FlaskClient


def module_list(client: FlaskClient, request_json: dict, status_code: int = 200) -> Iterator[list]:
    counter = 0
    amount = 12
    while amount == 12:
        request_json["counter"] = counter
        response: Response = client.post("/modules", json=request_json)
        assert response.status_code == status_code

        response_json = response.get_json()
        assert isinstance(response_json, list)
        yield response_json

        amount = len(response_json)
        assert amount < 13

        counter += 1

    assert counter > 0


def test_module_list(client: FlaskClient):
    assert len(list(module_list(client, {}))) > 0


def test_pinned_modules(client: FlaskClient):
    response: Response = client.post("/modules/3/preference/", json={"a": "pin"})
    assert response.status_code == 200
    assert response.get_json() == {"a": True}

    module_ids = []
    for response_json in module_list(client, {"filters": {"global": "pinned"}}):
        module_ids.extend([module["id"] for module in response_json])
    assert 3 in module_ids
