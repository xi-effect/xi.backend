from typing import Union

from requests import Response

from .library2 import MultiDoubleClient, DoubleClient


def check_status_code(response: Response, status_code: int = 200,
                      get_json: bool = True) -> Union[dict, list, Response]:
    assert response.status_code == status_code, response.json()
    return response.json() if get_json else response


def get_tr_io(multi_double_client: MultiDoubleClient) -> tuple[DoubleClient, DoubleClient, DoubleClient]:
    return multi_double_client.get_tr_io()  # noqa # I know better!!!
