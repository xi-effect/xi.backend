from __future__ import annotations

from typing import Optional, Callable

from sqlalchemy import Column, select, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import Select
from sqlalchemy.sql.sqltypes import Integer, String, Boolean

from common import User, UserRole, Base, sessionmaker, PydanticModel


class Author(Base, UserRole):
    __tablename__ = "authors"
    not_found_text = "Author does not exist"

    id = Column(Integer, ForeignKey(User.id), primary_key=True)
    pseudonym = Column(String(100), nullable=False)
    banned = Column(Boolean, nullable=False, default=False)
    last_image_id = Column(Integer, nullable=False, default=0)

    modules = relationship("Module", back_populates="author")

    @PydanticModel.include_columns(pseudonym, banned)
    class SettingsModel(PydanticModel):
        @classmethod
        def callback_convert(cls, callback: Callable, orm_object, **context) -> None:
            pass

    @classmethod
    def create(cls, session: sessionmaker, user: User) -> Author:
        new_entry = cls(pseudonym=user.username)
        user.author = new_entry
        session.add(new_entry)
        session.flush()
        return new_entry

    @classmethod
    def find_by_id(cls, session: sessionmaker, entry_id: int, include_banned: bool = False) -> Optional[Author]:
        stmt: Select = select(cls).filter_by(id=entry_id)
        if not include_banned:
            stmt = stmt.filter_by(banned=False)
        return session.get_first(stmt)

    @classmethod
    def find_or_create(cls, session: sessionmaker, user):  # User class
        if (author := cls.find_by_id(session, user.id, True)) is None:
            author = cls.create(session, user)
        return author

    @classmethod
    def initialize(cls, session: sessionmaker, user: User) -> bool:
        author = cls.find_or_create(session, user)
        return not author.banned

    def get_next_image_id(self) -> int:  # auto-commit
        self.last_image_id += 1
        return self.last_image_id  # noqa


class Moderator(Base, UserRole):
    __tablename__ = "moderators"
    not_found_text = "Permission denied"

    id = Column(Integer, ForeignKey(User.id), primary_key=True)

    @classmethod
    def find_by_id(cls, session: sessionmaker, entry_id: int) -> Moderator:
        return session.get_first(select(cls).filter_by(id=entry_id))

    @classmethod
    def create(cls, session: sessionmaker, user: User) -> bool:
        if cls.find_by_id(session, user.id):
            return False
        new_entry = cls()
        user.moderator = new_entry
        session.add(new_entry)
        session.flush()
        return True
