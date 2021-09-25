from json import load
from typing import Callable, Iterator, List, Optional

from flask.testing import FlaskClient
from pytest import mark

from xieffect.test.components import check_status_code


PER_REQUEST = 50


def check_deleting_ids(client: FlaskClient, list_tester: Callable[[str, dict, int], Iterator[dict]],
                       wip_type: str, ids: Optional[List[int]] = None):
    delete_all = ids is None

    for content_id in [data["id"] for data in list_tester(f"/{wip_type}s/owned", {}, PER_REQUEST)]:
        if delete_all or content_id in ids:
            check_status_code(client.delete(f"/wip/{wip_type}s/{content_id}"))

    assert not delete_all or len([data for data in list_tester(f"/{wip_type}s/owned", {}, PER_REQUEST)]) == 0


def check_editing(client: FlaskClient, list_tester: Callable[[str, dict, int], Iterator[dict]], wip_type: str):
    with open(f"test/json/sample-{wip_type}.json", "rb") as f:
        content: dict = load(f)

    assert (content_id := check_status_code(client.post(f"/wip/{wip_type}s", json=content)).get("id", None))
    assert any(content_id == data["id"] for data in list_tester(f"/{wip_type}s/owned", {}, PER_REQUEST))

    content["id"] = content_id
    assert check_status_code(client.get(f"/wip/{wip_type}s/{content_id}", json=content)) == content

    with open(f"test/json/sample-{wip_type}-2.json", "rb") as f:
        edited_content: dict = load(f)
    assert edited_content != content
    edited_content["id"] = content_id

    check_status_code(client.put(f"/wip/{wip_type}s/{content_id}", json=edited_content), get_json=False)
    assert check_status_code(client.get(f"/wip/{wip_type}s/{content_id}", json=edited_content)) == edited_content
    check_deleting_ids(client, list_tester, wip_type, [content_id])


@mark.order(200)
def test_delete_all_wip_pages(client: FlaskClient, list_tester: Callable[[str, dict, int], Iterator[dict]]):
    check_deleting_ids(client, list_tester, "page")
# https://discord.com/channels/706806130348785715/843536940083314728/880041704651108432


@mark.order(201)
def test_wip_page_editing(client: FlaskClient, list_tester: Callable[[str, dict, int], Iterator[dict]]):
    check_editing(client, list_tester, "page")
