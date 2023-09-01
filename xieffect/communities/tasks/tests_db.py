from __future__ import annotations

from typing import Self

from flask_fullstack import PydanticModel, Identifiable, TypeEnum
from sqlalchemy import Column, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import Integer, Text

from common import Base
from communities.tasks.main_db import Task


class QuestionKind(TypeEnum):
    SIMPLE = 0
    DETAILED = 1
    CHOICE = 2


class Question(Base, Identifiable):
    __tablename__ = "cs_questions"
    not_found_text = "Question not found"

    id = Column(Integer, primary_key=True)
    text = Column(Text, nullable=False)
    kind = Column(Enum(QuestionKind), nullable=False)
    test_id = Column(
        Integer,
        ForeignKey("cs_tests.id", ondelete="CASCADE"),
        nullable=False,
    )

    BaseModel = PydanticModel.column_model(text, kind)
    CreateModel = BaseModel.column_model(test_id)
    FullModel = BaseModel.column_model(id)

    @classmethod
    def create(cls, text: str, kind: QuestionKind, test_id: int) -> Self:
        return super().create(
            text=text,
            kind=kind,
            test_id=test_id,
        )

    def update(self, **kwargs) -> None:
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    @classmethod
    def find_by_id(cls, entry_id: int) -> Self | None:
        return cls.find_first_by_kwargs(id=entry_id)


class Test(Task):
    __test__ = False
    __tablename__ = "cs_tests"
    not_found_text = "Test not found"
    id = Column(
        Integer, ForeignKey("cs_tasks.id", ondelete="CASCADE"), primary_key=True
    )
    questions = relationship("Question", passive_deletes=True)

    FullModel = Task.FullModel.nest_model(Question.BaseModel, "questions", as_list=True)
