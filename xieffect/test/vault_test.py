from __future__ import annotations

from collections.abc import Iterable
from os.path import exists
from typing import TypeVar

from pytest import mark

from common import open_file
from test.conftest import BASIC_PASS, login, FlaskTestClient, create_file
from vault.files_db import FILES_PATH

k = TypeVar("k")
v = TypeVar("v")


def spread_dict(dct: dict[k, v], *keys: k, default=None) -> Iterable[v]:
    yield from (dct.get(key, default) for key in keys)


def assert_spread(dct: dict[k, v], *keys: k) -> Iterable[v]:
    for key in keys:
        result = dct.get(key)
        assert result is not None
        yield result


def upload(client: FlaskTestClient, filename: str) -> tuple[dict, bytes]:
    with open_file(f"xieffect/test/json/{filename}", "rb") as f:
        contents: bytes = f.read()
    data = client.post(
        "/files/",
        content_type="multipart/form-data",
        data={"file": create_file(filename, contents)},
    )

    file_id, server_filename = assert_spread(data, "id", "filename")
    assert server_filename == f"{file_id}-{filename}"
    return data, contents


@mark.order(70)
def test_files_normal(
    client: FlaskTestClient,
    mod_client: FlaskTestClient,
    base_client: FlaskTestClient,
):
    # saving file list for future checks
    previous_file_list = list(mod_client.paginate("/mub/files/"))

    # upload a file
    new_files: list[tuple[dict, bytes]] = [
        upload(client, filename) for filename in ("test-1.json", "test-2.json")
    ]
    new_files.reverse()

    # check file accessibility
    def assert_file_data(server_filename: str, real_data: bytes):
        client.get_file(f"/files/{server_filename}/", expected_data=real_data)
        mod_client.get_file(f"/files/{server_filename}/", expected_data=real_data)
        base_client.get_file(f"/files/{server_filename}/", expected_data=real_data)

    new_file_list = list(mod_client.paginate("/mub/files/"))
    for data, contents in new_files:
        assert new_file_list.pop(0) == data

        filename: str = data["filename"]
        filepath = FILES_PATH + filename
        assert exists(filepath)
        with open(filepath, "rb") as f:
            assert f.read() == contents

        assert_file_data(filename, contents)

    assert len(new_file_list) == len(previous_file_list)
    assert all(
        new_file_list[i] == previous_file_list[i]
        for i in range(len(previous_file_list))
    )

    # check deleting files
    stranger_client: FlaskTestClient = login("1@user.user", BASIC_PASS)

    for i, file in enumerate(new_files):
        file_id, filename = spread_dict(file[0], "id", "filename")
        stranger_client.delete(
            f"/files/manager/{file_id}/",
            expected_status=403,
            expected_a="Not your file",
        )

        if i % 2:
            client.delete(f"/files/manager/{file_id}/", expected_a=True)
            assert exists(FILES_PATH + filename)
        else:
            mod_client.delete(f"/mub/files/{file_id}/", expected_a=True)
            assert not exists(FILES_PATH + filename)
