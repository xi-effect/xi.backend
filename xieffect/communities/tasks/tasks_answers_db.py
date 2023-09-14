from __future__ import annotations

from typing import Self

from flask_fullstack import Identifiable, PydanticModel
from sqlalchemy import Column, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import Integer

from common.abstract import FileEmbed, SoftDeletable
from vault.files_db import File


class TaskAnswerFile(FileEmbed):
    __tablename__ = "cs_task_answer_embeds"

    task_answer_id = Column(
        Integer,
        ForeignKey("cs_task_answer.id", ondelete="CASCADE"),
        primary_key=True,
    )


class TaskAnswer(SoftDeletable, Identifiable):
    __tablename__ = "cs_task_answer"
    not_found_text = "Answer not found"

    id = Column(Integer, primary_key=True)
    task_id = Column(
        Integer,
        ForeignKey("cs_tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    task = relationship("Task")

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    user = relationship("User")

    page_id = Column(Integer, nullable=False)

    files = relationship(
        "File", secondary=TaskAnswerFile.__table__, passive_deletes=True
    )

    CreateModel = PydanticModel.column_model(task_id, user_id, page_id)

    IndexModel = CreateModel.column_model(id)

    FullModel = IndexModel.nest_model(File.FullModel, "files", as_list=True)

    @classmethod
    def find_by_id(cls, entry_id: int) -> Self | None:
        return cls.find_first_not_deleted(id=entry_id)

    @classmethod
    def create(
        cls,
        task_id: int,
        user_id: int,
        page_id: int,
    ) -> Self:
        return super().create(
            task_id=task_id,
            user_id=user_id,
            page_id=page_id,
        )
