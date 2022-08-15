from __future__ import annotations
from typing import Optional
from sqlalchemy import Column, select, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import Select
from sqlalchemy.sql.sqltypes import Integer, DateTime, Text
from __lib__.flask_fullstack import Identifiable
from common import User, Base, sessionmaker


class Task(Base, Identifiable):
    __tablename__ = "tasks"
    not_found_text = "Task does not exist"

    id = Column(Integer, primary_key=True)
    creator_id = Column(Integer, ForeignKey(User.id), nullable=False)
    category = Column(Text, nullable=False)
    title = Column(Text, nullable=False)
    date_time = Column(DateTime, nullable=False)
    duration = Column(Integer, nullable=False)

    @classmethod
    def find_by_id(cls, session: sessionmaker, entry_id: int) -> Optional[Task]:
        stmt: Select = select(cls).filter_by(id=entry_id)
        return session.get_first(stmt)


class UserTask(Base):
    __tablename__ = "user_tasks"
    not_found_text = "Record does not exist"

    user_id = Column(Integer, ForeignKey(User.id), primary_key=True, nullable=False)
    task_id = Column(Integer, ForeignKey(Task.id), primary_key=True, nullable=False)
    user = relationship(User)
    task = relationship(Task)

    @classmethod
    def find_by_id(cls, session: sessionmaker, user_id: int, task_id: int) -> Optional[UserTask]:
        stmt: Select = select(cls).filter_by(user_id=user_id, task_id=task_id)
        return session.get_first(stmt)
