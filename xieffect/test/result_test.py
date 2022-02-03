from random import randint
from typing import Iterator, Callable

from flask.testing import FlaskClient

from .components import check_status_code, dict_equal
from .knowledge_test import MODULES_PER_REQUEST


def test_result(client: FlaskClient, list_tester: Callable[[str, dict, int], Iterator[dict]]):
    # solver test
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
            json_test: dict = {"right-answers": 1, "total-answers": 1, "answers": {"1": 2}}
            assert check_status_code(client.post(f"/modules/{module_id}/points/{map_length}/reply/",
                                                 json=json_test)) == {"a": True}

            reply = check_status_code(client.get(f"/modules/{module_id}/points/{map_length}/reply"))
            assert reply == json_test["answers"]

            reply = check_status_code(client.get(f"/modules/{module_id}/results/"))["result"][0]
            assert dict_equal(reply, json_test, "right-answers", "total-answers", "answers")

    assert len(types_set) == 0

    module = check_status_code(client.get(f"/modules/7/"))
    print(module)
    assert module["type"] == "test"
    assert "map" in module.keys()

    length: int = len(module["map"])

    replies: list[dict] = [{
        "right-answers": (right := randint(0, 10)),
        "total-answers": (total := (randint(1, 5) if right == 0 else randint(right, right * 2))),
        "answers": {str(k): int(k) for k in range(randint(right, total))}
    } for _ in range(length)]

    point_ids: list[int] = list(range(length))
    for point in point_ids:
        assert check_status_code(client.get(f"/modules/7/points/{point}/reply/")) == {}
        check_status_code(client.get(f"/modules/7/points/{point}/"))
        assert check_status_code(client.get(f"/modules/7/points/{point}/reply/")) == {}

        # Get one result
        print(check_status_code(client.get(f"/results/{point}/"), get_json=True))

        # Delete one result
        assert check_status_code(client.delete(f"/results/{point}/"), get_json=False)

        # check_status_code(client.get(f"/results/{point}"), 404)
