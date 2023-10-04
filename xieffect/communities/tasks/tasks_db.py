from __future__ import annotations

from datetime import datetime
from typing import Self

from flask_fullstack import Identifiable, PydanticModel, TypeEnum
from sqlalchemy import Column, ForeignKey, select, or_
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import DateTime, Integer, String, Text

from common import db
from common.abstract import FileEmbed, SoftDeletable
from vault.files_db import File

TASKS_PER_PAGE: int = 48


class TaskEmbed(FileEmbed):
    __allow_unmapped__ = True
    __tablename__ = "cs_embeds"

    task_id = Column(
        Integer,
        ForeignKey("cs_tasks.id", ondelete="CASCADE"),
        primary_key=True,
    )


class TaskFilter(TypeEnum):
    ALL = 0
    ACTIVE = 1


class TaskOrder(TypeEnum):
    CREATED = 0
    OPENED = 1
    CLOSED = 2


class Task(SoftDeletable, Identifiable):
    __allow_unmapped__ = True
    __tablename__ = "cs_tasks"
    not_found_text = "Task not found"

    id = Column(Integer, primary_key=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    user = relationship("User", passive_deletes=True)

    community_id = Column(
        Integer,
        ForeignKey("community.id", ondelete="CASCADE"),
        nullable=False,
    )
    community = relationship("Community", passive_deletes=True)

    # TODO recheck the argument name after information pages will be added
    page_id = Column(Integer, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    created = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    opened = Column(DateTime, nullable=True, index=True)
    closed = Column(DateTime, nullable=True, index=True)

    files = relationship("File", secondary=TaskEmbed.__table__, passive_deletes=True)

    BaseModel = PydanticModel.column_model(id, created)
    CreateModel = PydanticModel.column_model(page_id, name, description, opened, closed)

    class IndexModel(BaseModel, CreateModel):
        username: str

        @classmethod
        def callback_convert(cls, callback, orm_object: Task, **_) -> None:
            callback(username=orm_object.user.username)

    FullModel = IndexModel.nest_model(File.FullModel, "files", as_list=True)

    @classmethod
    def find_by_id(cls, entry_id: int) -> Self | None:
        return cls.find_first_not_deleted(id=entry_id)

    @classmethod
    def create(
        cls,
        user_id: int,
        community_id: int,
        page_id: int,
        name: str,
        description: str | None = None,
        opened: datetime | None = None,
        closed: datetime | None = None,
    ) -> Self:
        return super().create(
            user_id=user_id,
            community_id=community_id,
            page_id=page_id,
            name=name,
            description=description,
            opened=opened,
            closed=closed,
        )

    def update(self, **kwargs) -> None:
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    @classmethod
    def get_paginated(
        cls,
        offset: int,
        limit: int,
        entry_filter: TaskFilter,
        entry_order: TaskOrder = TaskOrder.CREATED,
        open_only: bool = False,
        **kwargs,
    ) -> list[Self]:
        stmt = select(cls).filter_by(**kwargs).order_by(entry_order.name.lower())
        if open_only:
            stmt = stmt.filter(cls.opened <= datetime.utcnow())
        if entry_filter == TaskFilter.ACTIVE:
            stmt = stmt.filter(
                cls.opened <= datetime.utcnow(),
                or_(cls.closed > datetime.utcnow(), cls.closed.is_(None)),
            )
        return db.get_paginated(stmt, offset, limit)
