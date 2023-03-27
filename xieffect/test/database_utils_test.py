from __future__ import annotations

from datetime import datetime
from os.path import exists

from werkzeug.datastructures import FileStorage

from common import User, db, open_file
from other.database_cli import remove_stale
from test.conftest import FlaskTestClient
from test.vault_test import create_file, upload
from vault.files_db import File, FILES_PATH


def test_remove_stale(base_user_id: int):
    user: User = User.find_first_by_kwargs(id=base_user_id)
    filename: str = "test-1.json"

    with open_file(f"xieffect/test/json/{filename}", "rb") as f:
        contents: bytes = f.read()

    file_storage: FileStorage = create_file(filename, contents)
    file: File = File.create(user, file_storage.filename)
    file_id: int = file.id
    filename: str = file.filename
    file_storage.save(FILES_PATH + filename)
    assert exists(FILES_PATH + filename)

    file.deleted = datetime.utcnow()
    db.session.commit()

    remove_stale()
    assert File.find_first_by_kwargs(id=file_id) is None
    assert not exists(FILES_PATH + filename)


def test_soft_delete(client: FlaskTestClient):
    filename: str = "test-2.json"
    new_file: tuple[dict, bytes] = upload(client, filename)
    file_id: int | None = new_file[0].get("id")
    assert isinstance(file_id, int)
    assert File.find_by_id(file_id) is not None

    client.delete(f"/files/manager/{file_id}/", expected_a=True)
    deleted_file: File | None = File.find_first_by_kwargs(id=file_id)
    assert File.find_by_id(file_id) is None
    assert deleted_file is not None

    expiry_datetime: datetime = deleted_file.deleted
    expected_datetime: datetime = datetime.utcnow() + deleted_file.shelf_life
    assert expiry_datetime.date() == expected_datetime.date()
