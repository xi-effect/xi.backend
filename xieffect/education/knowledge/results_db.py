from __future__ import annotations

from typing import Union

from sqlalchemy import Column, ForeignKey, select
from sqlalchemy.sql.sqltypes import Integer, JSON

from common import User
from education.knowledge.interaction_db import TestModuleSession
from main import Base, Session


class TestResult(Base):
    __tablename__ = "TestResult"
    not_found_text = "Test not found"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    module_id = Column(Integer, ForeignKey("modules.id"), nullable=False)
    short_result = Column(JSON, nullable=False)
    result = Column(JSON, nullable=False)

    @classmethod
    def create(cls, session: Session, user_id: int, module_id: int) -> TestResult:
        new_entry = cls(user_id=user_id, module_id=module_id)
        session.add(new_entry)
        session.flush()
        return new_entry

    @classmethod
    def find_by_id(cls, session: Session, entry_id: int) -> Union[TestModuleSession, None]:
        return session.execute(select(cls).where(cls.id == entry_id)).scalars().first()

    @classmethod
    def find_by_user(cls, session: Session, user_id: int, offset: int, limit: int) -> list[User]:
        return session.execute(select(cls).filter_by(user_id=user_id).offset(offset).limit(limit)).scalars().all()

    @classmethod
    def find_by_module(cls, session: Session, user_id: int, module_id: int):
        return session.execute(select(cls).where(cls.user_id == user_id, cls.module_id == module_id)).scalars().first()

    def collect_all(self, session: Session):
        return self.result
