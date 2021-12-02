from typing import Union

from werkzeug.test import Response, TestResponse


def check_status_code(response: Union[TestResponse, Response], status_code: int = 200,
                      get_json: bool = True) -> Union[dict, list, Response, TestResponse]:
    assert response.status_code == status_code, response.get_json()
    return response.get_json() if get_json else response
