from __future__ import annotations

from collections.abc import Callable, Iterator

from flask.testing import FlaskClient
from pytest import mark

from flask_fullstack import check_code

MODULES_PER_REQUEST: int = 12


@mark.order(420)
def test_module_list(client: FlaskClient, list_tester: Callable[[str, dict, int], Iterator[dict]]):
    assert len(list(list_tester("/modules/", {}, MODULES_PER_REQUEST))) > 0
    assert check_code(client.post("/modules/", json={"counter": 0, "filters": "lol"}), 400)
    assert check_code(client.post("/modules/", json={"counter": 0, "filters": {"global": "lol"}}), 400)
    assert check_code(client.post("/modules/", json={"counter": 0, "filters": {"global": ["lol"]}}), 400)
    assert check_code(client.post("/modules/", json={"counter": 0, "sort": "lol"}), 400)


def lister_with_filters(list_tester: Callable[[str, dict, int], Iterator[dict]], filters: dict):
    return list_tester("/modules/", {"filters": filters}, MODULES_PER_REQUEST)


@mark.order(422)
def test_simple_module_filtering(list_tester: Callable[[str, dict, int], Iterator[dict]]):
    filter_map = {
        "theme": ["math", "languages", "geography"],
        "category": ["university", "prof-skills", "bne"],
        "difficulty": ["review", "amateur", "expert"]
    }

    for filter_name, values in filter_map.items():
        for filter_value in values:
            success: bool = False
            for module in lister_with_filters(list_tester, {filter_name: filter_value}):
                assert filter_name in module, module
                assert module[filter_name] == filter_value, module
                success = True
            assert success, f"No modules found for filter: {filter_name} == {filter_value}"


def assert_non_descending_order(
    dict_key: str, default: ... = None, /, revert: bool = False
) -> Callable[[dict, dict], None]:
    def assert_non_descending_order_inner(module1: dict, module2: dict):
        if revert:
            module1, module2 = module2, module1
        if default is None:
            assert dict_key in module1 and dict_key in module2
            assert module2[dict_key] >= module1[dict_key]
        else:
            assert module2.get(dict_key, default) >= module1.get(dict_key, default)

    return assert_non_descending_order_inner


@mark.order(425)
def test_module_sorting(list_tester: Callable[[str, dict, int], Iterator[dict]]):
    sort_types: dict[str, Callable[[dict, dict], None]] = {
        "popularity": assert_non_descending_order("views"),
        "creation-date": assert_non_descending_order("created", revert=True),
        "visit-date": assert_non_descending_order("visited", "", revert=True),
    }

    for sort_name, assert_in_order in sort_types.items():
        prev_module: dict | None = None
        for module in list_tester("/modules/", {"sort": sort_name}, MODULES_PER_REQUEST):
            if prev_module is not None:
                assert_in_order(prev_module, module)
            prev_module = module


@mark.skip
@mark.order(427)
def test_module_search(list_tester: Callable[[str, dict, int], Iterator[dict]]):
    assert len(list(list_tester("/modules/", {"search": "ЕГЭ"}, MODULES_PER_REQUEST))) > 0


def temp_list_tester(client: FlaskClient, module_id: int, include: bool):
    link: str = "/modules/"
    request_json: dict = {"filters": {"global": "starred"}}
    page_size: int = 12
    status_code: int = 200

    # copied from !list_tester! TODO make list_tester multiuser
    counter = 0
    amount = page_size
    while amount == page_size:
        request_json["counter"] = counter
        response_json: dict = check_code(client.post(link, json=request_json), status_code)

        assert "results" in response_json
        assert isinstance(response_json["results"], list)
        for content in response_json["results"]:
            # yield content
            # changed from !list_tester!
            assert "id" in content
            result = module_id == content["id"]
            assert result is include

        amount = len(response_json["results"])
        assert amount <= page_size

        counter += 1

    assert counter > 0
