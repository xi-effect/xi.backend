from __future__ import annotations

from collections.abc import Iterable
from io import BytesIO
from os.path import exists
from typing import TypeVar

from flask.testing import FlaskClient
from pytest import mark
from werkzeug.datastructures import FileStorage

from __lib__.flask_fullstack import check_code
from .conftest import BASIC_PASS, login

k = TypeVar("k")
v = TypeVar("v")


def spread_dict(dct: dict[k, v], *keys: k, default=None) -> Iterable[v]:
    yield from (dct.get(key, default) for key in keys)


def assert_spread(dct: dict[k, v], *keys: k) -> Iterable[v]:
    for key in keys:
        result = dct.get(key, None)
        assert result is not None
        yield result


def create_file(filename: str, contents: bytes):
    return FileStorage(stream=BytesIO(contents), filename=filename)


@mark.order(70)
def test_files_normal(client: FlaskClient, mod_client: FlaskClient, base_client: FlaskClient, list_tester):
    # saving file list for future checks
    previous_file_list = list(list_tester("/mub/files/index/", {}, 20))

    # upload a file
    def upload(filename: str):
        with open(f"test/education/json/{filename}", "rb") as f:
            contents: bytes = f.read()
        data = check_code(client.post(
            "/files/",
            content_type="multipart/form-data",
            data={"file": create_file(filename, contents)}
        ))

        file_id, server_filename = assert_spread(data, "id", "filename")
        assert server_filename == str(file_id) + "-" + filename
        return data, contents

    new_files: list[tuple[dict, bytes]] = [upload(filename) for filename in ("sample-page.json", "sample-page-2.json")]
    new_files.reverse()

    # check file accessibility
    def assert_file_data(server_filename: str, real_data: bytes):
        assert check_code(client.get(f"/files/{server_filename}/"), get_json=False).data == real_data
        assert check_code(mod_client.get(f"/files/{server_filename}/"), get_json=False).data == real_data
        assert check_code(base_client.get(f"/files/{server_filename}/"), get_json=False).data == real_data

    new_file_list = list(list_tester("/mub/files/index/", {}, 20))
    for data, contents in new_files:
        assert new_file_list.pop(0) == data
        assert_file_data(data["filename"], contents)

        filename: str = data["filename"]
        filepath = f"../files/vault/{filename}"
        assert exists(filepath)
        with open(filepath, "rb") as f:
            assert f.read() == contents

    assert len(new_file_list) == len(previous_file_list)
    assert all(new_file_list[i] == previous_file_list[i] for i in range(len(previous_file_list)))

    # check deleting files
    stranger_client: FlaskClient = login("1@user.user", BASIC_PASS)

    for i, file in enumerate(new_files):
        file_id, filename = spread_dict(file[0], "id", "filename")
        assert check_code(stranger_client.delete(f"/files/manager/{file_id}/"), 403)["a"] == "Not your file"
        assert check_code(stranger_client.delete(f"/mub/files/{file_id}/"), 403)["a"] == "Permission denied"

        if i % 2:
            assert check_code(client.delete(f"/files/manager/{file_id}/"))["a"]
        else:
            assert check_code(mod_client.delete(f"/mub/files/{file_id}/"))["a"]

        assert not exists(f"../files/vault/{filename}")
