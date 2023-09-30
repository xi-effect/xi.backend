from __future__ import annotations

from datetime import timedelta
from typing import Self

from flask_fullstack import PydanticModel
from sqlalchemy import Column, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import Integer, Text

from common import db, User, absolute_path
from common.abstract import SoftDeletable

FILES_PATH: str = absolute_path("files/vault/")


class File(SoftDeletable):
    __tablename__ = "files"
    not_found_text = "File not found"

    id: int | Column = Column(Integer, primary_key=True)
    name: str | Column = Column(Text, nullable=False)
    shelf_life: timedelta = timedelta(days=1)  # TODO: discuss timedelta

    uploader_id: int | Column = Column(
        Integer,
        ForeignKey(User.id, ondelete="CASCADE"),
        nullable=False,
    )
    uploader: User | relationship = relationship(
        User,
        foreign_keys=[uploader_id],
        passive_deletes=True,
    )

    @PydanticModel.include_columns(id)
    class FullModel(PydanticModel):
        filename: str

        @classmethod
        def callback_convert(cls, callback, orm_object: File, **_) -> None:
            callback(filename=orm_object.filename)  # TODO allow this in FFS simpler!

    @classmethod
    def create(cls, uploader: User, name: str) -> Self:
        return super().create(name=name, uploader=uploader)

    @classmethod
    def find_by_id(cls, entry_id: int) -> Self | None:
        return cls.find_first_not_deleted(id=entry_id)

    @classmethod
    def find_by_ids(cls, entry_ids: list) -> list[Self]:
        stmt = cls.select_not_deleted().filter(cls.id.in_(entry_ids))
        return db.get_all(stmt)

    @property
    def filename(self) -> str:
        return f"{self.id}-{self.name}"

    @classmethod
    def get_for_mub(cls, offset: int, limit: int) -> list[Self]:
        return cls.find_paginated_by_kwargs(offset, limit, cls.id.desc())
