from __future__ import annotations

from typing import Self

from flask_fullstack import PydanticModel, Identifiable, TypeEnum
from sqlalchemy import Column, ForeignKey, update, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import Integer, Text

from common import db
from common.abstract import SoftDeletable
from communities.tasks.main_db import Task


class QuestionKind(TypeEnum):
    SIMPLE = 0
    DETAILED = 1
    CHOICE = 2


class Question(SoftDeletable, Identifiable):
    __tablename__ = "cs_questions"
    not_found_text = "Question not found"

    id = Column(Integer, primary_key=True)
    text = Column(Text, nullable=False)
    kind = Column("type", Enum(QuestionKind))
    test_id = Column(
        Integer,
        ForeignKey("cs_tests.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )

    BaseModel = PydanticModel.column_model(text, kind)
    CreateModel = BaseModel.column_model(test_id)

    @classmethod
    def create(cls, text: str, kind: QuestionKind, test_id: int) -> Self:
        return super().create(
            text=text,
            kind=kind,
            test_id=test_id,
        )

    @classmethod
    def update(cls, question_id: int, **kwargs) -> None:
        db.session.execute(update(cls).filter(cls.id == question_id).values(**kwargs))

    @classmethod
    def find_by_id(cls, entry_id: int) -> Self | None:
        return cls.find_first_not_deleted(id=entry_id)


class Test(Task):
    __tablename__ = "cs_tests"
    not_found_text = "Test not found"
    id = Column(Integer, ForeignKey("cs_tasks.id"), primary_key=True)
    questions = relationship("Question", passive_deletes=True)

    FullModel = Task.FullModel.nest_model(Question.BaseModel, "questions", as_list=True)
