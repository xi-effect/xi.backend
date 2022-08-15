from __future__ import annotations

from typing import Optional

from sqlalchemy import Column, select, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import Select
from sqlalchemy.sql.sqltypes import Integer, String, DateTime, Float

from common import User, UserRole, Base, sessionmaker, PydanticModel


class Task(Base, UserRole):
    __tablename__ = "tasks"
    unauthorized_error = (403, "Task does not exist")

    id = Column(Integer, primary_key=True, autoincrement=True)
    creator_id = Column(Integer, ForeignKey(User.id))
    category = Column(String(255))
    title = Column(String(255))
    date_time = Column(DateTime)
    duration = Column(Float)

    @classmethod
    def find_by_id(cls, session: sessionmaker, entry_id: int, include_banned: bool = False) -> Optional[Task]:
        stmt: Select = select(cls).filter_by(id=entry_id)
        if not include_banned:
            stmt = stmt.filter_by(banned=False)
        return session.get_first(stmt)

    @classmethod
    def find_by_identity(cls, session, identity: int) -> Task | None:
        return cls.find_by_id(session, identity)

    def get_identity(self):
        return self.id


class User_Task(Base, UserRole):
    __tablename__ = "users_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey(User.id))
    task_id = Column(Integer, ForeignKey(Task.id))
    user = relationship(User)
    task = relationship(Task)

    @classmethod
    def find_by_id(cls, session: sessionmaker, entry_id: int, include_banned: bool = False) -> Optional[User_Task]:
        stmt: Select = select(cls).filter_by(id=entry_id)
        if not include_banned:
            stmt = stmt.filter_by(banned=False)
        return session.get_first(stmt)

    @classmethod
    def find_by_identity(cls, session, identity: int) -> User_Task | None:
        return cls.find_by_id(session, identity)

    def get_identity(self):
        return self.id
