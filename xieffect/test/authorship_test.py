from json import load
from typing import Callable, Iterator

from flask.testing import FlaskClient
from pytest import mark

from xieffect.test.components import check_status_code


@mark.order(10)
def test_wip_page_creating(client: FlaskClient, list_tester: Callable[[str, dict, int], Iterator[list]]):
    with open("xieffect/test/json/sample-page.json", "rb") as f:
        sample_page: dict = load(f)

    assert (page_id := check_status_code(client.post("/wip/pages", json=sample_page)).get_json().get("a", None))
    assert any(page_id == data["id"] for page_page in list_tester("/wip/pages/index", {}, 20) for data in page_page)

    sample_page["id"] = page_id
    assert check_status_code(client.get(f"/wip/pages/{page_id}", json=sample_page)).get_json() == sample_page


@mark.order(11)
def test_wip_page_editing(client: FlaskClient, list_tester: Callable[[str, dict, int], Iterator[list]]):
    with open("xieffect/test/json/sample-page.json", "rb") as f:
        sample_page: dict = load(f)
    assert (page_id := check_status_code(client.post("/wip/pages", json=sample_page)).get_json().get("a", None))

    page: dict = check_status_code(client.get(f"/wip/pages/{page_id}")).get_json()
    assert page_id == page["id"]

    with open("xieffect/test/json/sample-page-2.json", "rb") as f:
        edited_page: dict = load(f)
    assert edited_page != sample_page
    edited_page["id"] = page_id
    assert page != edited_page

    check_status_code(client.put(f"/wip/pages/{page_id}", json=edited_page))
    assert check_status_code(client.get(f"/wip/pages/{page_id}", json=edited_page)).get_json() == edited_page


def test_wip_module(client: FlaskClient):
    pass
