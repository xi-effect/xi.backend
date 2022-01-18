from __future__ import annotations

from typing import Union

from sqlalchemy import Column, ForeignKey, select
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import Integer, String, Boolean, JSON, DateTime, Text, Enum

from common import Identifiable, Marshalable, LambdaFieldDef, create_marshal_model, register_as_searchable, TypeEnum, User
from education.knowledge.interaction_db import TestModuleSession
from main import Base, Session


@create_marshal_model("TestResult", "short_result", "result")
class TestResult(Base):
    __tablename__ = "TestResult"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    module_id = Column(Integer, ForeignKey("module.id"), nullable=False)
    short_result = Column(JSON)
    result = Column(JSON)

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