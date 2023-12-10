from __future__ import annotations

from typing import Self

from flask_fullstack import Identifiable, TypeEnum
from pydantic_marshals.base.fields.base import PatchDefault
from pydantic_marshals.sqlalchemy import MappedModel
from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common import Base
from communities.tasks.tasks_db import Task


class QuestionKind(TypeEnum):
    SIMPLE = 0
    DETAILED = 1
    CHOICE = 2


class Question(Base, Identifiable):
    __tablename__ = "cs_questions"
    not_found_text = "Question not found"

    id: Mapped[int] = mapped_column(primary_key=True)
    text: Mapped[str] = mapped_column(Text)
    kind: Mapped[QuestionKind] = mapped_column()
    test_id: Mapped[int] = mapped_column(
        ForeignKey("cs_tests.id", ondelete="CASCADE"),
    )

    BaseModel = MappedModel.create(columns=[text, kind])
    UpdateModel = BaseModel.as_patch()
    FullModel = BaseModel.extend(columns=[id])

    @classmethod
    def create(cls, text: str, kind: QuestionKind, test_id: int) -> Self:
        return super().create(
            text=text,
            kind=kind,
            test_id=test_id,
        )

    def update(self, **kwargs) -> None:
        for key, value in kwargs.items():
            if value is not PatchDefault and hasattr(self, key):
                setattr(self, key, value)

    @classmethod
    def find_by_id(cls, entry_id: int) -> Self | None:
        return cls.find_first_by_kwargs(id=entry_id)


class Test(Task):
    __test__ = False
    __tablename__ = "cs_tests"
    not_found_text = "Test not found"

    id: Mapped[int] = mapped_column(
        ForeignKey("cs_tasks.id", ondelete="CASCADE"),
        primary_key=True,
    )
    questions: Mapped[list[Question]] = relationship(
        passive_deletes=True,
    )

    FullModel = Task.__dict__["FullModel"].extend(
        relationships=[(questions, Question.BaseModel)],
    )
