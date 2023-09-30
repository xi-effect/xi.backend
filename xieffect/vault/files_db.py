from __future__ import annotations

from datetime import timedelta
from typing import Self, ClassVar

from pydantic_marshals.sqlalchemy import MappedModel
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql.sqltypes import Text

from common import db, User, absolute_path
from common.abstract import SoftDeletable
from common.pydantic import v2_model_to_ffs

FILES_PATH: str = absolute_path("files/vault/")


class File(SoftDeletable):
    __tablename__ = "files"
    not_found_text = "File not found"
    shelf_life: ClassVar[timedelta] = timedelta(days=1)  # TODO: discuss timedelta

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(Text)

    uploader_id: Mapped[int] = mapped_column(ForeignKey(User.id, ondelete="CASCADE"))
    uploader: Mapped[User] = relationship(
        foreign_keys=[uploader_id],
        passive_deletes=True,
    )

    @property
    def filename(self) -> str:
        return f"{self.id}-{self.name}"

    FullModel = MappedModel.create(columns=[id], properties=[filename])

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

    @classmethod
    def get_for_mub(cls, offset: int, limit: int) -> list[Self]:
        return cls.find_paginated_by_kwargs(offset, limit, cls.id.desc())


File.FullModel = v2_model_to_ffs(File.FullModel)
