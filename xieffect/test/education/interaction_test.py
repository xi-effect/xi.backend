from __future__ import annotations

from collections.abc import Callable, Iterator

from flask.testing import FlaskClient
from flask_fullstack import check_code, dict_equal
from pytest import mark
from werkzeug.test import TestResponse

from .module_list_test import MODULES_PER_REQUEST


@mark.order(500)
def test_module_type_errors(client: FlaskClient, list_tester: Callable[[str, dict, int], Iterator[dict]]):
    types_set: set[str] = {"standard", "practice-block", "theory-block", "test"}

    for module in list_tester("/modules/", {}, MODULES_PER_REQUEST):
        module_id = module["id"]
        module_type = module["type"]
        module = check_code(client.get(f"/modules/{module_id}/"))

        if len(types_set) == 0:
            break
        if module_type not in types_set:
            continue
        types_set.remove(module_type)

        if module_type in {"standard", "practice-block"}:
            check_code(client.post(f"/modules/{module_id}/next/"))
            assert (
                check_code(client.get(f"/modules/{module_id}/points/0/"), 400)
                == {"a": f"Module of type {module_type} can't use direct navigation"}
            )

        if module_type in {"theory-block", "test"}:
            assert "map" in module
            map_length = len(module["map"]) - 1
            check_code(client.get(f"/modules/{module_id}/points/{map_length}/"))
            assert (
                check_code(client.post(f"/modules/{module_id}/next/"), 400)
                == {"a": f"Module of type {module_type} can't use linear progression"}
            )

        if module_type in {"practice-block", "test"}:
            assert (
                check_code(client.get(f"/modules/{module_id}/open/"), 400)
                == {"a": f"Module of type {module_type} can't use progress saving"}
            )

        if module_type == "test":
            assert "map" in module
            map_length = len(module["map"]) - 1
            json_test: dict = {"right-answers": 1, "total-answers": 1, "answers": {"1": 2}}
            assert check_code(
                client.post(
                    f"/modules/{module_id}/points/{map_length}/reply/",
                    json=json_test
                )
            ).get("a", False)

            reply = check_code(client.get(f"/modules/{module_id}/points/{map_length}/reply"))
            assert reply == json_test["answers"]

            reply = check_code(client.get(f"/modules/{module_id}/results/"))["result"][0]
            assert dict_equal(reply, json_test, "right-answers", "total-answers", "answers")
    else:
        raise AssertionError("Did not manage to find all module types")


@mark.order(510)
def test_standard_module_session(client: FlaskClient):  # relies on module#5
    module = check_code(client.get("/modules/5/"))
    assert module["type"] == "standard"

    def scroll_through() -> Iterator[int]:
        while True:
            result: TestResponse = check_code(client.post("/modules/5/next/"), get_json=False)
            if len(result.history) == 0:
                assert result.get_json() == {"a": "You have reached the end"}
                break

            page: dict = result.get_json()
            assert "id" in page
            yield page["id"]

    for _ in scroll_through():  # noqa: WPS328
        pass  # if any session was started before, reset the module

    ids1: list[int] = list(scroll_through())
    ids2: list[int] = list(scroll_through())

    assert ids1 == ids2

    assert all(ids1[i] < ids1[i + 1] for i in range(len(ids1) - 1))


@mark.order(520)
def test_module_navigation(client: FlaskClient):  # relies on module#9
    module = check_code(client.get("/modules/9/"))
    assert module["type"] == "theory-block"

    assert "map" in module
    length = len(module["map"])

    for point_id in range(length):
        check_code(client.get(f"/modules/9/points/{point_id}/"))
    check_code(client.get(f"/modules/9/points/{length}/"), 404)


@mark.order(530)  # relies on module#5 and module#9 (point#8 & point#9)
def test_module_opener(client: FlaskClient):  # pragma: no coverage
    if (response_json := check_code(client.post("/modules/5/next/"))) == {"a": "You have reached the end"}:
        response_json = check_code(client.post("/modules/5/next/"))
    assert check_code(client.get("/modules/5/open/")) == response_json

    check_code(client.get("/modules/9/points/8/"))
    assert check_code(client.get("/modules/9/open/")) == {"id": 8}
    check_code(client.get("/modules/9/points/9/"))
    assert check_code(client.get("/modules/9/open/")) == {"id": 9}