from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import Column, select, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import Select
from sqlalchemy.sql.sqltypes import Integer, String, Boolean

from common import User, UserRole, Base, db, PydanticModel


class Author(Base, UserRole):
    __tablename__ = "authors"
    unauthorized_error = (403, "Author does not exist")

    id = Column(Integer, ForeignKey(User.id), primary_key=True)
    pseudonym = Column(String(100), nullable=False)
    banned = Column(Boolean, nullable=False, default=False)
    last_image_id: int | Column = Column(Integer, nullable=False, default=0)

    modules = relationship("Module", back_populates="author")

    @PydanticModel.include_columns(pseudonym, banned)
    class SettingsModel(PydanticModel):
        @classmethod
        def callback_convert(cls, callback: Callable, orm_object, **context) -> None:
            pass

    @classmethod
    def create(cls, user: User) -> Author:
        new_entry = cls(pseudonym=user.username)
        user.author = new_entry
        db.session.add(new_entry)
        db.session.flush()
        return new_entry

    @classmethod
    def find_by_id(
        cls,
        entry_id: int,
        include_banned: bool = False,
    ) -> Author | None:
        stmt: Select = select(cls).filter_by(id=entry_id)
        if not include_banned:
            stmt = stmt.filter_by(banned=False)
        return db.session.get_first(stmt)

    @classmethod
    def find_by_identity(cls, identity: int) -> Author | None:
        return cls.find_by_id(identity)

    @classmethod
    def find_or_create(cls, user):  # User class
        if (author := cls.find_by_id(user.id, include_banned=True)) is None:
            return cls.create(user)
        return author

    @classmethod
    def initialize(cls, user: User) -> bool:
        author = cls.find_or_create(user)
        return not author.banned

    def get_identity(self):
        return self.id

    def get_next_image_id(self) -> int:  # auto-commit
        self.last_image_id += 1
        return self.last_image_id
