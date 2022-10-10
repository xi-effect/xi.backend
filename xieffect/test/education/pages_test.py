from __future__ import annotations

from collections.abc import Callable, Iterator
from json import load as load_json

from flask.testing import FlaskClient
from pytest import mark

from flask_fullstack import check_code

PAGES_PER_REQUEST: int = 50


@mark.order(400)
def test_page_list(list_tester: Callable[[str, dict, int], Iterator[dict]]):
    assert len(list(list_tester("/pages/", {}, PAGES_PER_REQUEST))) > 0


@mark.skip()  # TODO fix whoosh search not saving the index
@mark.order(401)
def test_searching_pages(list_tester: Callable[[str, dict, int], Iterator[dict]]):
    assert len(list(list_tester("/pages/", {"search": "Описание test"}, PAGES_PER_REQUEST))) > 0


@mark.order(406)
def test_getting_pages(client: FlaskClient):
    page_json: dict = check_code(client.get("/pages/1/"))

    with open("../static/test/page-bundle.json", "rb") as f:
        file_content: dict = load_json(f)[0]
    for key in ("blueprint", "reusable", "public"):
        file_content.pop(key)

    assert page_json == file_content


@mark.order(407)
def test_page_view_counter(client: FlaskClient, list_tester: Callable[[str, dict, int], Iterator[dict]]):
    page_json: dict = check_code(client.post("/pages/", json={"counter": 0}))["results"][0]
    page_id, views_before = [page_json[key] for key in ("id", "views")]
    check_code(client.get(f"/pages/{page_id}/"), get_json=False)

    for page_json in list_tester("/pages/", {}, PAGES_PER_REQUEST):
        if page_json["id"] == page_id:
            assert page_json["views"] == views_before + 1
            break
    else:
        raise AssertionError(f"Page with id={page_id} wasn't found")
