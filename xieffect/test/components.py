from typing import Union

from flask import Response


def check_status_code(response: Response, status_code: int = 200, get_json: bool = True) -> Union[dict, list, Response]:
    assert response.status_code == status_code, response.get_json()
    return response.get_json() if get_json else response
