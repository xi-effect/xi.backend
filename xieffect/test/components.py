from typing import Union

from werkzeug.test import Response, TestResponse


def check_status_code(response: Union[TestResponse, Response], status_code: int = 200,
                      get_json: bool = True) -> Union[dict, list, Response, TestResponse]:
    assert response.status_code == status_code, response.get_json()
    return response.get_json() if get_json else response


def dict_equal(dict1: dict, dict2: dict, *keys) -> bool:
    dict1 = {key: dict1.get(key, None) for key in keys}
    dict2 = {key: dict2.get(key, None) for key in keys}
    return dict1 == dict2
