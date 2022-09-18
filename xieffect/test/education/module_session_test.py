from __future__ import annotations

from collections.abc import Callable, Iterator

from flask.testing import FlaskClient
from pytest import mark

from __lib__.flask_fullstack import check_code
from .module_list_test import MODULES_PER_REQUEST, lister_with_filters, temp_list_tester


def get_some_module_id(
    list_tester: Callable[[str, dict, int], Iterator[dict]],
    check: Callable[[dict], bool] = None
) -> int | None:
    module_id: int | None = None
    for module in list_tester("/modules/", {}, MODULES_PER_REQUEST):
        assert "id" in module
        if check is None or check(module):
            module_id = module["id"]
            break
    return module_id


def assert_with_global_filter(
    client: FlaskClient,
    list_tester: Callable[[str, dict, int], Iterator[dict]],
    operation_name: str,
    filter_name: str,
    url: str,
    module_id: int,
    reverse: bool
):
    if reverse:
        operation_name = "un" + operation_name
        iterator: Iterator[dict] = list_tester("/modules/", {}, MODULES_PER_REQUEST)
    else:
        iterator: Iterator[dict] = lister_with_filters(list_tester, {"global": filter_name})

    assert check_code(client.post(url + "preference/", json={"a": operation_name})) == {"a": True}

    result: dict = check_code(client.get(url))
    assert result[filter_name] != reverse

    success: bool = False
    for module in iterator:
        assert filter_name in module
        assert module[filter_name] != reverse
        if module["id"] == module_id:
            success = True
    assert success, (
        f"Module #{module_id}, marked as "
        + ("un" if reverse else "")
        + f"{filter_name}, was "
        + ("" if reverse else "not ")
        + f"found in the list of {filter_name} modules"
    )


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
        assert_with_global_filter(client, list_tester, operation_name, filter_name, url, module_id, reverse=False)
        assert_with_global_filter(client, list_tester, operation_name, filter_name, url, module_id, reverse=True)


def assert_hidden(list_tester: Callable[[str, dict, int], Iterator[dict]], module_id: int, reverse: bool):
    message = f"Module #{module_id}, marked as "
    message += "shown" if reverse else "hidden"
    message += ", was "

    found: bool = False
    for hidden_module in list_tester("/modules/hidden/", {}, MODULES_PER_REQUEST):
        assert "id" in hidden_module
        if hidden_module["id"] == module_id:
            found = True
            break
    assert found != reverse, message + ("" if reverse else "not ") + "found in the list of hidden modules"  # noqa: WPS509

    found: bool = False
    for module in list_tester("/modules/", {}, MODULES_PER_REQUEST):
        assert "id" in module
        if module["id"] == module_id:
            found = True
            break
    assert found == reverse, message + ("not " if reverse else "") + "found in normal modules"  # noqa: WPS509


def set_module_hidden(client: FlaskClient, module_id: int, hidden: bool):
    data = {"a": "hide" if hidden else "show"}
    assert check_code(client.post(f"/modules/{module_id}/preference/", json=data))["a"]


@mark.order(430)
def test_hiding_modules(client: FlaskClient, list_tester: Callable[[str, dict, int], Iterator[dict]]):
    module_id: int = get_some_module_id(list_tester)
    set_module_hidden(client, module_id, hidden=True)
    assert_hidden(list_tester, module_id, reverse=False)

    set_module_hidden(client, module_id, hidden=False)
    assert_hidden(list_tester, module_id, reverse=True)


@mark.order(431)
def test_hidden_module_ordering(client: FlaskClient, list_tester: Callable[[str, dict, int], Iterator[dict]]):
    module_id1: int = get_some_module_id(list_tester)
    module_id2: int = get_some_module_id(list_tester, lambda module: module["id"] != module_id1)
    assert module_id1 is not None and module_id2 is not None, "Couldn't find two modules"
    assert module_id1 != module_id2, "Function get_some_module_id() returned same module_id twice"

    set_module_hidden(client, module_id1, hidden=True)
    set_module_hidden(client, module_id2, hidden=True)

    met_module_id2: bool = False
    for module in list_tester("/modules/hidden/", {}, MODULES_PER_REQUEST):
        assert "id" in module
        if module["id"] == module_id2:
            met_module_id2 = True
        if module["id"] == module_id1:
            assert met_module_id2, f"Met module_id1 ({module_id1}) before module_id2 ({module_id2})"
            break
    else:
        assert met_module_id2, f"Met neither module_id1 ({module_id1}), nor module_id2 ({module_id2})"
        raise AssertionError(f"Didn't meet module_id1 ({module_id1})")

    set_module_hidden(client, module_id1, hidden=False)
    set_module_hidden(client, module_id2, hidden=False)


@mark.order(423)
def test_module_filtering_multiuser(
    multi_client: Callable[[str], FlaskClient],
    list_tester: Callable[[str, dict, int], Iterator[dict]]
):
    user1: FlaskClient = multi_client("1@user.user")
    user2: FlaskClient = multi_client("2@user.user")
    module_id: int = get_some_module_id(list_tester)

    assert check_code(user1.post(f"/modules/{module_id}/preference/", json={"a": "star"})) == {"a": True}
    assert check_code(user2.post(f"/modules/{module_id}/preference/", json={"a": "unstar"})) == {"a": True}

    temp_list_tester(user1, module_id, include=True)
    temp_list_tester(user2, module_id, include=False)
