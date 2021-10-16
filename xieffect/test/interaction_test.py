from typing import Iterator, Callable

from flask.testing import FlaskClient
from werkzeug.test import TestResponse

from .components import check_status_code
from .knowledge_test import MODULES_PER_REQUEST


def test_module_type_errors(client: FlaskClient, list_tester: Callable[[str, dict, int], Iterator[dict]]):
    for module in list_tester("/modules/", {}, MODULES_PER_REQUEST):
        module_id = module["id"]
        module_type = module["type"]
        module = check_status_code(client.get(f"/modules/{module_id}/"))

        if module_type in ("standard", "practice-block"):
            check_status_code(client.post(f"/modules/{module_id}/next/"))
            assert check_status_code(client.get(f"/modules/{module_id}/points/0/"), 400) == \
                   {"a": f"Module of type {module_type} can't use direct navigation"}

        elif module_type in ("theory-block", "test"):
            assert "map" in module.keys()
            map_length = len(module["map"]) - 1
            check_status_code(client.get(f"/modules/{module_id}/points/{map_length}/"))
            assert check_status_code(client.post(f"/modules/{module_id}/next/"), 400) == \
                   {"a": f"Module of type {module_type} can't use linear progression"}

        elif module_type == "test":
            pass
