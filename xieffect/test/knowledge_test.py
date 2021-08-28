from json import load
from typing import Callable, Iterator

from flask.testing import FlaskClient
from pytest import mark

from xieffect.test.components import check_status_code


@mark.order(400)
def test_module_list(list_tester: Callable[[str, dict, int], Iterator[dict]]):
    assert len(list(list_tester("/modules", {}, 12))) > 0


@mark.order(401)
def test_pinned_modules(client: FlaskClient, list_tester: Callable[[str, dict, int], Iterator[dict]]):
    assert check_status_code(client.post("/modules/3/preference/", json={"a": "pin"})) == {"a": True}

    module_ids = [module["id"] for module in list_tester("/modules", {"filters": {"global": "pinned"}}, 12)]
    assert 3 in module_ids

    assert check_status_code(client.post("/modules/3/preference/", json={"a": "unpin"})) == {"a": True}

    module_ids = [module["id"] for module in list_tester("/modules", {"filters": {"global": "pinned"}}, 12)]
    assert 3 not in module_ids


@mark.order(402)
def test_page_list(list_tester: Callable[[str, dict, int], Iterator[dict]]):
    assert len(list(list_tester("/pages", {}, 50))) > 0


@mark.order(403)
def test_searching_pages(list_tester: Callable[[str, dict, int], Iterator[list]]):
    assert len(list(list_tester("/pages", {"search": "Описание test"}, 50))) > 0


@mark.order(406)
def test_getting_pages(client: FlaskClient):
    page_json: dict = check_status_code(client.get("/pages/1"))
    page_json["components"] = check_status_code(client.get("/pages/1/components"))
    page_json.pop("author_id")
    page_json.pop("author_name")

    with open("files/tfs/test/1.json", "rb") as f:
        assert page_json == load(f)
