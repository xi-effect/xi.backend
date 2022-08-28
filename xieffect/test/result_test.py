from collections.abc import Iterator, Callable
from random import randint  # noqa: DUO102

from flask.testing import FlaskClient
from pytest import mark

from __lib__.flask_fullstack import check_code, dict_equal


@mark.order(545)
def test_result(client: FlaskClient, list_tester: Callable[[str, dict, int], Iterator[dict]]):
    # solve test
    module = check_code(client.get("/modules/7/"))
    assert module["type"] == "test"
    assert "map" in module

    length: int = len(module["map"])

    def generate_reply():
        return {
            "right-answers": (right := randint(0, 10)),
            "total-answers": (total := (randint(1, 5) if right == 0 else randint(right, right * 2))),
            "answers": {str(k): int(k) for k in range(randint(right, total))}
        }

    replies: list[dict] = [generate_reply() for _ in range(length)]

    point_ids: list[int] = list(range(length))
    for point in point_ids:
        data = check_code(client.get(f"/modules/7/points/{point}/reply/"))
        assert isinstance(data, dict) and len(data) == 0
        check_code(client.get(f"/modules/7/points/{point}/"))
        data = check_code(client.get(f"/modules/7/points/{point}/reply/"))
        assert isinstance(data, dict) and len(data) == 0

        reply = replies[point]
        assert check_code(client.post(f"/modules/7/points/{point}/reply/", json=reply)) == {"a": True}
        assert check_code(client.get(f"/modules/7/points/{point}/reply/")) == reply["answers"]

    result1 = check_code(client.get("/modules/7/results/"))
    result_id = result1["id"]

    results = list(list_tester("/results/modules/7/", {}, 50))
    assert len(results) > 0
    dict_equal(result1, results[0], "id", "module_id")

    result2 = check_code(client.get(f"/results/{result_id}/"))
    assert result2 == result1
    for i, data in enumerate(result2["result"]):
        dict_equal(data, replies[i], "right-answers", "total-answers", "answers")

    check_code(client.delete(f"/results/{result_id}/"))
    check_code(client.get(f"/results/{result_id}/"), 404)
