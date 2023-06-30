from __future__ import annotations

from typing import Self

from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship

from common import User
from communities.base.discussion_db import Discussion, DiscussionMessage


class TaskDiscussionMessage(DiscussionMessage):
    __tablename__ = "task_ds_messages"
    not_found_text = "Discussion message not found"

    id: Column | int = Column(Integer, ForeignKey("ds_messages.id"), primary_key=True)

    @classmethod
    def find_paginated(cls, offset: int, limit: int, *args, **kwargs) -> list[Self]:
        return cls.find_paginated_by_kwargs(offset, limit, *args, **kwargs)


class TaskDiscussion(Discussion):
    __tablename__ = "cs_task_discussions"
    not_found_text = "Task discussion not found"

    id: Column | int = Column(Integer, ForeignKey("discussions.id"), primary_key=True)

    task_id: Column | int = Column(
        Integer,
        ForeignKey("cs_tasks.id"),
        nullable=False,
    )
    task = relationship("Task")

    student_id: Column | int = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
    )
    student: User = relationship("User")

    @classmethod
    def create(
        cls,
        task_id: int,
        student_id: int,
    ) -> Self:
        return super().create(
            task_id=task_id,
            student_id=student_id,
        )
