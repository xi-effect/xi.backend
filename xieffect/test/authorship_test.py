from json import load
from typing import Callable, Iterator

from flask.testing import FlaskClient
from pytest import mark

from xieffect.test.components import check_status_code


def check_creating(client: FlaskClient, list_tester: Callable[[str, dict, int], Iterator[list]], wip_type: str):
    with open(f"xieffect/test/json/sample-{wip_type}.json", "rb") as f:
        content: dict = load(f)

    assert (content_id := check_status_code(client.post(f"/wip/{wip_type}s", json=content)).get("a", None))
    assert any(content_id == data["id"] for page in list_tester(f"/wip/{wip_type}s/index", {}, 20) for data in page)

    content["id"] = content_id
    assert check_status_code(client.get(f"/wip/{wip_type}s/{content_id}", json=content)) == content


def check_editing(client: FlaskClient, wip_type: str):
    with open(f"xieffect/test/json/sample-{wip_type}.json", "rb") as f:
        content: dict = load(f)
    assert (content_id := check_status_code(client.post(f"/wip/{wip_type}s", json=content)).get("a", None))

    page: dict = check_status_code(client.get(f"/wip/{wip_type}s/{content_id}"))
    assert content_id == page["id"]

    with open(f"xieffect/test/json/sample-{wip_type}-2.json", "rb") as f:
        edited_content: dict = load(f)
    assert edited_content != content
    edited_content["id"] = content_id
    assert page != edited_content

    check_status_code(client.put(f"/wip/{wip_type}s/{content_id}", json=edited_content), get_json=False)
    assert check_status_code(client.get(f"/wip/{wip_type}s/{content_id}", json=edited_content)) == edited_content


@mark.order(10)
def test_wip_page_creating(client: FlaskClient, list_tester: Callable[[str, dict, int], Iterator[list]]):
    check_creating(client, list_tester, "page")


@mark.order(11)
def test_wip_page_editing(client: FlaskClient):
    check_editing(client, "page")
