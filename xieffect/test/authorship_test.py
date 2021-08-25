from json import load
from typing import Callable, Iterator, List, Optional

from flask.testing import FlaskClient
from pytest import mark

from xieffect.test.components import check_status_code


def check_deleting_ids(client: FlaskClient, list_tester: Callable[[str, dict, int], Iterator[list]],
                       wip_type: str, ids: Optional[List[int]] = None):
    delete_all = ids is None

    for content_id in [c["id"] for page in list_tester(f"/wip/{wip_type}s/index", {}, 20) for c in page]:
        if delete_all or content_id in ids:
            check_status_code(client.delete(f"/wip/{wip_type}s/{content_id}"))

    assert not delete_all or len([d for page in list_tester(f"/wip/{wip_type}s/index", {}, 20) for d in page]) == 0


def check_editing(client: FlaskClient, list_tester: Callable[[str, dict, int], Iterator[list]], wip_type: str):
    with open(f"xieffect/test/json/sample-{wip_type}.json", "rb") as f:
        content: dict = load(f)

    assert (content_id := check_status_code(client.post(f"/wip/{wip_type}s", json=content)).get("id", None))
    assert any(content_id == data["id"] for page in list_tester(f"/wip/{wip_type}s/index", {}, 20) for data in page)

    content["id"] = content_id
    assert check_status_code(client.get(f"/wip/{wip_type}s/{content_id}", json=content)) == content

    with open(f"xieffect/test/json/sample-{wip_type}-2.json", "rb") as f:
        edited_content: dict = load(f)
    assert edited_content != content
    edited_content["id"] = content_id

    check_status_code(client.put(f"/wip/{wip_type}s/{content_id}", json=edited_content), get_json=False)
    assert check_status_code(client.get(f"/wip/{wip_type}s/{content_id}", json=edited_content)) == edited_content
    check_deleting_ids(client, list_tester, wip_type, [content_id])


@mark.order(10)
def test_delete_all_wip_pages(client: FlaskClient, list_tester: Callable[[str, dict, int], Iterator[list]]):
    check_deleting_ids(client, list_tester, "page")
# https://discord.com/channels/706806130348785715/843536940083314728/880041704651108432


@mark.order(11)
def test_wip_page_editing(client: FlaskClient, list_tester: Callable[[str, dict, int], Iterator[list]]):
    check_editing(client, list_tester, "page")
