from json import load
from typing import Callable, Iterator, Optional, Dict, Any

from flask.testing import FlaskClient
from pytest import mark

from xieffect.test.components import check_status_code

PAGES_PER_REQUEST: int = 50
MODULES_PER_REQUEST: int = 12


@mark.order(400)
def test_page_list(list_tester: Callable[[str, dict, int], Iterator[dict]]):
    assert len(list(list_tester("/pages/", {}, PAGES_PER_REQUEST))) > 0


@mark.order(401)
def test_searching_pages(list_tester: Callable[[str, dict, int], Iterator[dict]]):
    assert len(list(list_tester("/pages/", {"search": "Описание test"}, PAGES_PER_REQUEST))) > 0


@mark.order(406)
def test_getting_pages(client: FlaskClient):
    page_json: dict = check_status_code(client.get("/pages/1/"))

    with open("../files/test/page-bundle.json", "rb") as f:
        file_content: dict = load(f)[0]
    for key in ("blueprint", "reusable", "public"):
        file_content.pop(key)

    assert page_json == file_content


@mark.order(407)
def test_page_view_counter(client: FlaskClient, list_tester: Callable[[str, dict, int], Iterator[dict]]):
    page_json: dict = check_status_code(client.post("/pages/", json={"counter": 0}))["results"][0]
    page_id, views_before = [page_json[key] for key in ["id", "views"]]
    check_status_code(client.get(f"/pages/{page_id}/"), get_json=False)

    for page_json in list_tester("/pages/", {}, PAGES_PER_REQUEST):
        if page_json["id"] == page_id:
            assert page_json["views"] == views_before + 1
            break
    else:
        raise AssertionError(f"Page with id={page_id} wasn't found")


@mark.order(420)
def test_module_list(client: FlaskClient, list_tester: Callable[[str, dict, int], Iterator[dict]]):
    assert len(list(list_tester("/modules/", {}, MODULES_PER_REQUEST))) > 0
    assert check_status_code(client.post("/modules/", json={"counter": 0, "filters": "lol"}), 400)
    assert check_status_code(client.post("/modules/", json={"counter": 0, "filters": {"global": "lol"}}), 400)
    assert check_status_code(client.post("/modules/", json={"counter": 0, "filters": {"global": ["lol"]}}), 400)
    assert check_status_code(client.post("/modules/", json={"counter": 0, "sort": "lol"}), 400)


def get_some_module_id(list_tester: Callable[[str, dict, int], Iterator[dict]],
                       check: Optional[Callable[[dict], bool]] = None) -> Optional[int]:
    module_id: Optional[int] = None
    for module in list_tester("/modules/", {}, MODULES_PER_REQUEST):
        assert "id" in module.keys()
        if check is None or check(module):
            module_id = module["id"]
            break
    return module_id


def lister_with_filters(list_tester: Callable[[str, dict, int], Iterator[dict]], filters: dict):
    return list_tester("/modules/", {"filters": filters}, MODULES_PER_REQUEST)


def assert_with_global_filter(client: FlaskClient, list_tester: Callable[[str, dict, int], Iterator[dict]],
                              operation_name: str, filter_name: str, url: str, module_id: int, reverse: bool):
    if reverse:
        operation_name = "un" + operation_name
        iterator: Iterator[dict] = list_tester("/modules/", {}, MODULES_PER_REQUEST)
    else:
        iterator: Iterator[dict] = lister_with_filters(list_tester, {"global": filter_name})

    assert check_status_code(client.post(url + "preference/", json={"a": operation_name})) == {"a": True}

    result: dict = check_status_code(client.get(url))
    assert result[filter_name] != reverse

    success: bool = False
    for module in iterator:
        assert filter_name in module.keys()
        assert module[filter_name] != reverse
        if module["id"] == module_id:
            success = True
    assert success, f"Module #{module_id}, marked as " + ("un" if reverse else "") + f"{filter_name}, was " \
                    + ("" if reverse else "not ") + f"found in the list of {filter_name} modules"


@mark.order(421)
def test_global_module_filtering(client: FlaskClient, list_tester: Callable[[str, dict, int], Iterator[dict]]):
    filter_to_operation = {
        "pinned": "pin",
        "starred": "star",
    }

    module_id: int = get_some_module_id(list_tester, lambda module: not (module["pinned"] or module["starred"]))
    assert module_id is not None, "No not-pinned and not-starred modules found"
    url: str = f"/modules/{module_id}/"

    for filter_name, operation_name in filter_to_operation.items():
        assert_with_global_filter(client, list_tester, operation_name, filter_name, url, module_id, False)
        assert_with_global_filter(client, list_tester, operation_name, filter_name, url, module_id, True)


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
                assert filter_name in module.keys(), module
                assert module[filter_name] == filter_value, module
                success = True
            assert success, f"No modules found for filter: {filter_name} == {filter_value}"


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
        response_json: dict = check_status_code(client.post(link, json=request_json), status_code)

        assert "results" in response_json
        assert isinstance(response_json["results"], list)
        for content in response_json["results"]:
            # yield content
            # changed from !list_tester!
            assert "id" in content.keys()
            assert (content["id"] == module_id) == include

        amount = len(response_json["results"])
        assert amount <= page_size

        counter += 1

    assert counter > 0


@mark.order(423)
def test_module_filtering_multiuser(multi_client: Callable[[str], FlaskClient],
                                    list_tester: Callable[[str, dict, int], Iterator[dict]]):
    user1: FlaskClient = multi_client("1@user.user")
    user2: FlaskClient = multi_client("2@user.user")
    module_id: int = get_some_module_id(list_tester)

    assert check_status_code(user1.post(f"/modules/{module_id}/preference/", json={"a": "star"})) == {"a": True}
    assert check_status_code(user2.post(f"/modules/{module_id}/preference/", json={"a": "unstar"})) == {"a": True}

    temp_list_tester(user1, module_id, True)
    temp_list_tester(user2, module_id, False)


def assert_non_descending_order(dict_key: str, default: Optional[Any] = None,
                                /, revert: bool = False) -> Callable[[dict, dict], None]:
    def assert_non_descending_order_inner(module1: dict, module2: dict):
        if revert:
            module1, module2 = module2, module1
        if default is None:
            assert dict_key in module1.keys() and dict_key in module2.keys()
            assert module2[dict_key] >= module1[dict_key]
        else:
            assert module2.get(dict_key, default) >= module1.get(dict_key, default)

    return assert_non_descending_order_inner


@mark.order(425)
def test_module_sorting(client: FlaskClient, list_tester: Callable[[str, dict, int], Iterator[dict]]):
    sort_types: Dict[str, Callable[[dict, dict], None]] = {
        "popularity": assert_non_descending_order("views"),
        "creation-date": assert_non_descending_order("created", revert=True),
        "visit-date": assert_non_descending_order("visited", "", revert=True),
    }

    for sort_name, assert_in_order in sort_types.items():
        prev_module: Optional[dict] = None
        for module in list_tester("/modules/", {"sort": sort_name}, MODULES_PER_REQUEST):
            if prev_module is not None:
                assert_in_order(prev_module, module)
            prev_module = module


@mark.order(427)
def test_module_search(list_tester: Callable[[str, dict, int], Iterator[dict]]):
    assert len(list(list_tester("/modules/", {"search": "ЕГЭ"}, MODULES_PER_REQUEST))) > 0


def assert_hidden(list_tester: Callable[[str, dict, int], Iterator[dict]], module_id: int, reverse: bool):
    message = f"Module #{module_id}, marked as " + ("shown" if reverse else "hidden") + ", was "

    found: bool = False
    for hidden_module in list_tester("/modules/hidden/", {}, MODULES_PER_REQUEST):
        assert "id" in hidden_module.keys()
        if hidden_module["id"] == module_id:
            found = True
            break
    assert found != reverse, message + ("" if reverse else "not ") + "found in the list of hidden modules"

    found: bool = False
    for module in list_tester("/modules/", {}, MODULES_PER_REQUEST):
        assert "id" in module.keys()
        if module["id"] == module_id:
            found = True
            break
    assert found == reverse, message + ("not " if reverse else "") + "found in normal modules"


def set_module_hidden(client: FlaskClient, module_id: int, hidden: bool):
    assert check_status_code(client.post(f"/modules/{module_id}/preference/",
                                         json={"a": "hide" if hidden else "show"})) == {"a": True}


@mark.order(430)
def test_hiding_modules(client: FlaskClient, list_tester: Callable[[str, dict, int], Iterator[dict]]):
    module_id: int = get_some_module_id(list_tester)
    set_module_hidden(client, module_id, True)
    assert_hidden(list_tester, module_id, False)

    set_module_hidden(client, module_id, False)
    assert_hidden(list_tester, module_id, True)


@mark.order(431)
def test_hidden_module_ordering(client: FlaskClient, list_tester: Callable[[str, dict, int], Iterator[dict]]):
    module_id1: int = get_some_module_id(list_tester)
    module_id2: int = get_some_module_id(list_tester, lambda module: module["id"] != module_id1)
    assert module_id1 is not None and module_id2 is not None, "Couldn't find two modules"
    assert module_id1 != module_id2, "Function get_some_module_id() returned same module_id twice"

    set_module_hidden(client, module_id1, True)
    set_module_hidden(client, module_id2, True)

    met_module_id2: bool = False
    for module in list_tester("/modules/hidden/", {}, MODULES_PER_REQUEST):
        assert "id" in module.keys()
        if module["id"] == module_id2:
            met_module_id2 = True
        if module["id"] == module_id1:
            assert met_module_id2, f"Met module_id1 ({module_id1}) before module_id2 ({module_id2})"
            break
    else:
        assert met_module_id2, f"Met neither module_id1 ({module_id1}), nor module_id2 ({module_id2})"
        assert False, f"Didn't meet module_id1 ({module_id1})"

    set_module_hidden(client, module_id1, False)
    set_module_hidden(client, module_id2, False)
