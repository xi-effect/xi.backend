from __future__ import annotations

from flask_restx import fields
from sqlalchemy import Column, ForeignKey
from sqlalchemy.sql.sqltypes import Integer

from common import JSONWithModel, Base, sessionmaker, PydanticModel
from .interaction_db import TestModuleSession
from .modules_db import Module

result_model = {
    "right-answers": fields.Integer,
    "total-answers": fields.Integer,
    "page-id": fields.Integer,
    "point-id": fields.Integer,
    "answers": fields.Raw,
}

short_result_model = {
    "module-name": fields.String,
    "author-id": fields.Integer,
    "author-name": fields.String,
    "right-answers": fields.Integer,
    "total-answers": fields.Integer,
}


class TestResult(Base):
    __tablename__ = "TestResult"
    not_found_text = "not found result"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    module_id = Column(Integer, ForeignKey("modules.id"), nullable=False)

    # TODO start_date = Column(DateTime, nullable=False)
    # TODO finish_date = Column(DateTime, nullable=False)
    short_result = Column(
        JSONWithModel("ShortResultInner", short_result_model), nullable=False
    )
    result = Column(
        JSONWithModel("FullResultInner", result_model, as_list=True), nullable=False
    )

    BaseModel = PydanticModel.column_model(id, module_id)
    ShortModel = BaseModel.column_model(short_result, _flatten_jsons=True)
    FullModel = BaseModel.column_model(result)

    @classmethod
    def create(
        cls,
        session: sessionmaker,
        user_id: int,
        module: Module,
        result,
    ) -> TestResult:
        short_result = {
            "module-name": module.name,
            "author-id": module.author.id,
            "author-name": module.author.pseudonym,
            "right-answers": sum(r["right-answers"] for r in result),
            "total-answers": sum(r["total-answers"] for r in result),
        }
        return super().create(
            session,
            user_id=user_id,
            module_id=module.id,
            short_result=short_result,
            result=result,
        )

    @classmethod
    def find_by_id(
        cls,
        session: sessionmaker,
        entry_id: int,
    ) -> TestModuleSession | None:
        return cls.find_first_by_kwargs(session, id=entry_id)

    @classmethod
    def find_by_user(
        cls,
        session: sessionmaker,
        user_id: int,
        offset: int,
        limit: int,
    ) -> list[TestModuleSession]:
        return cls.find_paginated_by_kwargs(
            session,
            offset,
            limit,
            cls.id.desc(),
            user_id=user_id,
        )

    @classmethod
    def find_by_module(
        cls,
        session: sessionmaker,
        user_id: int,
        module_id: int,
        offset: int,
        limit: int,
    ) -> list[TestModuleSession]:
        return cls.find_paginated_by_kwargs(
            session,
            offset,
            limit,
            cls.id.desc(),
            user_id=user_id,
            module_id=module_id,
        )
