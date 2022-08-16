from __future__ import annotations

from sqlalchemy import Column, ForeignKey, select
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import Integer, Text

from common import Base, User


class File(Base):
    __tablename__ = "files"

    id: int | Column = Column(Integer, primary_key=True)
    name: str | Column = Column(Text, nullable=False)

    uploader_id: int | Column = Column(Integer, ForeignKey(User.id), nullable=False)
    uploader = relationship(User)

    @classmethod
    def create(cls, session, uploader: User, name: str) -> File:
        return super().create(session, name=name, uploader=uploader)

    @classmethod
    def find_by_id(cls, session, entry_id: int) -> File | None:
        return session.get_first(select(cls).filter_by(id=entry_id))

    @property
    def filename(self):
        return self.id + "-" + self.name
