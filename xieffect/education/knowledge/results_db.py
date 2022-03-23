from __future__ import annotations

from typing import Union

from flask_restx import fields
from sqlalchemy import Column, ForeignKey, select
from sqlalchemy.sql.sqltypes import Integer

from common import JSONWithModel, create_marshal_model, Marshalable, Base, sessionmaker
from .interaction_db import TestModuleSession
from .modules_db import Module

result_model = {
    "right-answers": fields.Integer,
    "total-answers": fields.Integer,
    "page-id": fields.Integer,
    "point-id": fields.Integer,
    "answers": fields.Raw
}

short_result_model = {
    "module-name": fields.String,
    "author-id": fields.Integer,
    "author-name": fields.String,
    "right-answers": fields.Integer,
    "total-answers": fields.Integer,
}


@create_marshal_model("full-result", "result", inherit="base-result")
@create_marshal_model("short-result", "short_result", flatten_jsons=True, inherit="base-result")
@create_marshal_model("base-result", "id", "module_id")
class TestResult(Base, Marshalable):
    __tablename__ = "TestResult"
    not_found_text = "not found result"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    module_id = Column(Integer, ForeignKey("modules.id"), nullable=False)

    # TODO start_date = Column(DateTime, nullable=False)
    # TODO finish_date = Column(DateTime, nullable=False)
    short_result = Column(JSONWithModel("ShortResultInner", short_result_model), nullable=False)
    result = Column(JSONWithModel("FullResultInner", result_model, as_list=True), nullable=False)

    @classmethod
    def create(cls, session: sessionmaker, user_id: int, module: Module, result) -> TestResult:
        short_result = {
            "module-name": module.name,
            "author-id": module.author.id,
            "author-name": module.author.pseudonym,
            "right-answers": sum(r["right-answers"] for r in result),
            "total-answers": sum(r["total-answers"] for r in result),
        }

        new_entry = cls(user_id=user_id, module_id=module.id, short_result=short_result, result=result)  # noqa
        session.add(new_entry)
        session.flush()
        return new_entry

    @classmethod
    def find_by_id(cls, session: sessionmaker, entry_id: int) -> Union[TestModuleSession, None]:
        return session.execute(select(cls).filter_by(id=entry_id)).scalars().first()

    @classmethod
    def find_by_user(cls, session: sessionmaker, user_id: int, offset: int, limit: int) -> list[TestModuleSession]:
        stmt = select(cls).filter_by(user_id=user_id).order_by(cls.id.desc())
        return session.execute(stmt.offset(offset).limit(limit)).scalars().all()

    @classmethod
    def find_by_module(cls, session: sessionmaker, user_id: int, module_id: int,
                       offset: int, limit: int) -> list[TestModuleSession]:
        stmt = select(cls).filter_by(user_id=user_id, module_id=module_id).order_by(cls.id.desc())
        return session.execute(stmt.offset(offset).limit(limit)).scalars().all()

    def delete(self, session: sessionmaker):
        session.delete(self)
        session.flush()
