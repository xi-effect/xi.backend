from __future__ import annotations

from typing import Self

from flask_fullstack import PydanticModel, Identifiable
from sqlalchemy import Column, ForeignKey
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import Integer, String, JSON

from common.abstract import SoftDeletable


class Page(SoftDeletable, Identifiable):  # pragma: no coverage
    __tablename__ = "pages"
    not_found_text = "Page not found"

    id = Column(Integer, primary_key=True)
    title = Column(String(100), nullable=False)
    content = Column(MutableDict.as_mutable(JSON), nullable=False)

    creator_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL", onupdate="CASCADE")
    )
    creator = relationship("User")

    CreateModel = PydanticModel.column_model(title, content)
    IndexModel = CreateModel.column_model(id, creator_id)

    @classmethod
    def create(cls, title: str, content: dict, creator_id: int) -> Self:
        return super().create(title=title, content=content, creator_id=creator_id)

    @classmethod
    def find_by_id(cls, entry_id: int) -> Self | None:
        return cls.find_first_not_deleted(id=entry_id)
