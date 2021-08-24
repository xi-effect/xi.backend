from flask import Response


def check_status_code(response: Response, status_code: int = 200) -> Response:
    assert response.status_code == status_code, response.get_json()
    return response
