from __future__ import annotations

from datetime import datetime
from os.path import exists

from common import db
from other.database_cli import remove_stale
from test.conftest import FlaskTestClient
from vault.files_db import File, FILES_PATH


def test_remove_stale(test_file_id: int):
    file: File = File.find_by_id(test_file_id)
    file_id: int = file.id
    filename: str = file.filename
    assert exists(FILES_PATH + filename)

    file.deleted = datetime.utcnow()
    db.session.commit()

    remove_stale()
    assert File.find_first_by_kwargs(id=file_id) is None
    assert not exists(FILES_PATH + filename)


def test_soft_delete(fresh_client: FlaskTestClient, test_file_id: int):
    fresh_client.delete(f"/files/manager/{test_file_id}/", expected_a=True)
    deleted_file: File | None = File.find_first_by_kwargs(id=test_file_id)
    assert File.find_by_id(test_file_id) is None
    assert deleted_file is not None

    expiry_datetime: datetime = deleted_file.deleted
    expected_datetime: datetime = datetime.utcnow() + deleted_file.shelf_life
    assert expiry_datetime.date() == expected_datetime.date()
