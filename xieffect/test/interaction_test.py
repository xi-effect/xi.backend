from typing import Iterator, Callable

from flask.testing import FlaskClient
from pytest import mark
from werkzeug.test import TestResponse

from .components import check_status_code
from .knowledge_test import MODULES_PER_REQUEST


@mark.order(500)
def test_module_type_errors(client: FlaskClient, list_tester: Callable[[str, dict, int], Iterator[dict]]):
    types_set: set[str] = {"standard", "practice-block", "theory-block", "test"}

    for module in list_tester("/modules/", {}, MODULES_PER_REQUEST):
        module_id = module["id"]
        module_type = module["type"]
        module = check_status_code(client.get(f"/modules/{module_id}/"))

        if len(types_set) == 0:
            return
        if module_type not in types_set:
            continue
        types_set.remove(module_type)

        if module_type in ("standard", "practice-block"):
            check_status_code(client.post(f"/modules/{module_id}/next/"))
            assert check_status_code(client.get(f"/modules/{module_id}/points/0/"), 400) == \
                   {"a": f"Module of type {module_type} can't use direct navigation"}

        if module_type in ("theory-block", "test"):
            assert "map" in module.keys()
            map_length = len(module["map"]) - 1
            check_status_code(client.get(f"/modules/{module_id}/points/{map_length}/"))
            assert check_status_code(client.post(f"/modules/{module_id}/next/"), 400) == \
                   {"a": f"Module of type {module_type} can't use linear progression"}

        if module_type in ("practice-block", "test"):
            assert check_status_code(client.get(f"/modules/{module_id}/open/"), 400) == \
                   {"a": f"Module of type {module_type} can't use progress saving"}

        if module_type == "test":
            assert "map" in module.keys()
            map_length = len(module["map"]) - 1
            json_test: dict = {"right-answers": 1,
                               "total-answers": 1,
                               "answers": {"1": 2}}
            reply_json = check_status_code(
                client.post(f"/modules/{module_id}/points/{map_length}/reply/", json=json_test))
            assert reply_json == {"a": True}



    assert len(types_set) == 0


@mark.order(510)
def test_standard_module_session(client: FlaskClient):  # relies on module#5
    module = check_status_code(client.get("/modules/5/"))
    assert module["type"] == "standard"

    def scroll_through() -> Iterator[int]:
        while True:
            result: TestResponse = check_status_code(client.post("/modules/5/next/"), get_json=False)
            if len(result.history):  # it was redirected
                page: dict = result.get_json()
                assert "id" in page.keys()
                yield page["id"]
            else:
                assert result.get_json() == {"a": "You have reached the end"}
                break

    for _ in scroll_through():
        pass  # if any session was started before, reset the module

    ids1: list[int] = [page_id for page_id in scroll_through()]
    ids2: list[int] = [page_id for page_id in scroll_through()]

    assert ids1 == ids2

    assert all(ids1[i] < ids1[i + 1] for i in range(len(ids1) - 1))


@mark.order(520)
def test_module_navigation(client: FlaskClient):  # relies on module#9
    module = check_status_code(client.get("/modules/9/"))
    assert module["type"] == "theory-block"

    assert "map" in module.keys()
    length = len(module["map"])

    for point_id in range(length):
        check_status_code(client.get(f"/modules/9/points/{point_id}/"))
    check_status_code(client.get(f"/modules/9/points/{length}/"), 404)


@mark.order(530)
def test_module_opener(client: FlaskClient):  # relies on module#5 and module#9 (point#8 & point#9)
    if (response_json := check_status_code(client.post("/modules/5/next/"))) == {"a": "You have reached the end"}:
        response_json = check_status_code(client.post("/modules/5/next/"))
    assert check_status_code(client.get("/modules/5/open/")) == response_json

    response_json = check_status_code(client.get("/modules/9/points/8/"))
    assert check_status_code(client.get("/modules/9/open/")) == response_json
    response_json = check_status_code(client.get("/modules/9/points/9/"))
    assert check_status_code(client.get("/modules/9/open/")) == response_json
