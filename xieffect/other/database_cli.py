from __future__ import annotations

from datetime import datetime
from os import remove

from flask import Blueprint
from sqlalchemy import delete, select
from sqlalchemy.sql import Delete

from common import Base, db
from vault.files_db import FILES_PATH

remove_stale_blueprint = Blueprint("database", __name__)


def remove_stale() -> None:
    for table in Base.metadata.sorted_tables:
        if "deleted" in table.columns:
            filter_condition = table.c.deleted <= datetime.utcnow()
            stmt: Delete = delete(table).filter(filter_condition)
            if table.name == "files":
                files: list = db.get_all_rows(select(table).filter(filter_condition))
                for file in files:
                    remove(f"{FILES_PATH}{file.id}-{file.name}")
            db.session.execute(stmt)
            db.session.commit()


@remove_stale_blueprint.cli.command("remove_stale")
def remove_stale_cli() -> None:  # TODO pragma: no coverage
    remove_stale()
