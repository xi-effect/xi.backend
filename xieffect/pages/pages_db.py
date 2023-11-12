from __future__ import annotations

from typing import Self

from flask_fullstack import Identifiable
from pydantic_marshals.sqlalchemy import MappedModel
from sqlalchemy import Column
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.sqltypes import Integer, String, JSON

from common.abstract import SoftDeletable


class Page(SoftDeletable, Identifiable):  # pragma: no coverage
    __tablename__ = "pages"
    not_found_text = "Page not found"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    content: Mapped[dict] = Column(MutableDict.as_mutable(JSON), nullable=False)

    creator_id: Mapped[int] = mapped_column(Integer)

    CreateModel = MappedModel.create(columns=[title, content])
    IndexModel = CreateModel.extend(columns=[id, creator_id])

    @classmethod
    def create(cls, title: str, content: dict, creator_id: int) -> Self:
        return super().create(title=title, content=content, creator_id=creator_id)

    @classmethod
    def find_by_id(cls, entry_id: int) -> Self | None:
        return cls.find_first_not_deleted(id=entry_id)
