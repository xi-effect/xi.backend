from __future__ import annotations

from sqlalchemy import Column, ForeignKey, select
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import Integer, Text

from common import PydanticModel, Base, User


class File(Base):
    __tablename__ = "files"
    not_found_text = "File not found"

    id: int | Column = Column(Integer, primary_key=True)
    name: str | Column = Column(Text, nullable=False)

    uploader_id: int | Column = Column(Integer, ForeignKey(User.id), nullable=False)
    uploader: User | relationship = relationship(User)

    @PydanticModel.include_columns(id)
    class FullModel(PydanticModel):
        filename: str

        @classmethod
        def callback_convert(cls, callback, orm_object: File, **_):
            callback(filename=orm_object.filename)  # TODO allow this in FFS simpler!

    @classmethod
    def create(cls, session, uploader: User, name: str) -> File:
        return super().create(session, name=name, uploader=uploader)

    @classmethod
    def find_by_id(cls, session, entry_id: int) -> File | None:
        return session.get_first(select(cls).filter_by(id=entry_id))

    @property
    def filename(self) -> str:
        return str(self.id) + "-" + self.name

    @classmethod
    def get_for_mub(cls, session, offset: int, limit: int) -> list[File]:
        return session.get_paginated(
            select(File).order_by(cls.id.desc()), offset, limit
        )
