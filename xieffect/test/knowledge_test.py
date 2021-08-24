from typing import Callable, Iterator, Optional
from pytest import mark

from flask import Response
from flask.testing import FlaskClient


@mark.order(6)
def test_module_list(client: FlaskClient, list_tester: Callable[[str, dict, int], Iterator[list]]):
    assert len(list(list_tester("/modules", {}, 12))) > 0


@mark.order(7)
def test_pinned_modules(client: FlaskClient, list_tester: Callable[[str, dict, int], Iterator[list]]):
    response: Response = client.post("/modules/3/preference/", json={"a": "pin"})
    assert response.status_code == 200
    assert response.get_json() == {"a": True}

    module_ids = []
    for response_json in list_tester("/modules", {"filters": {"global": "pinned"}}, 12):
        module_ids.extend([module["id"] for module in response_json])
    assert 3 in module_ids
