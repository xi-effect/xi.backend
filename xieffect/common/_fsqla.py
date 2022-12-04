from __future__ import annotations

from typing import TypeVar

from flask_sqlalchemy import SQLAlchemy as _SQLAlchemy
from sqlalchemy.engine import Row
from sqlalchemy.sql import Select

t = TypeVar("t")
m = TypeVar("m", bound="SQLAlchemy.Model")


# TODO proper type annotations for Select (mb python3.11's Self type)
# noinspection PyUnresolvedReferences
class SQLAlchemy(_SQLAlchemy):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app.after_request(self.with_autocommit)

    def with_autocommit(self, result: t = None) -> t:
        self.session.commit()
        return result

    def get_first(self, stmt: Select) -> m | None:
        return self.session.execute(stmt).scalars().first()

    def get_first_row(self, stmt: Select) -> Row:
        return self.session.execute(stmt).first()

    def get_all(self, stmt: Select) -> list[m]:
        return self.session.execute(stmt).scalars().all()

    def get_all_rows(self, stmt: Select) -> list[Row]:
        return self.session.execute(stmt).all()

    def get_paginated(self, stmt: Select, offset: int, limit: int) -> list[m]:
        return self.get_all(stmt.offset(offset).limit(limit))

    def get_paginated_rows(self, stmt: Select, offset: int, limit: int) -> list[Row]:
        return self.get_all_rows(stmt.offset(offset).limit(limit))
