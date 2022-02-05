from random import randint
from typing import Iterator, Callable

from pytest import mark
from flask.testing import FlaskClient

from .components import check_status_code, dict_equal


@mark.order(545)
def test_result(client: FlaskClient, list_tester: Callable[[str, dict, int], Iterator[dict]]):
    # solve test
    module = check_status_code(client.get(f"/modules/7/"))
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

        reply = replies[point]
        assert check_status_code(client.post(f"/modules/7/points/{point}/reply/", json=reply)) == {"a": True}
        assert check_status_code(client.get(f"/modules/7/points/{point}/reply/")) == reply["answers"]

    result1 = check_status_code(client.get(f"/modules/7/results/"))
    result_id = result1["id"]

    results = list(list_tester("/results/modules/7/", {}, 50))
    assert len(results) > 0
    dict_equal(result1, results[0], "id", "module_id")

    result2 = check_status_code(client.get(f"/results/{result_id}/"))
    assert result2 == result1
    for i in range(len(result2["result"])):
        dict_equal(result2["result"][i], replies[i], "right-answers", "total-answers", "answers")

    check_status_code(client.delete(f"/results/{result_id}/"))
    check_status_code(client.get(f"/results/{result_id}/"), 404)
