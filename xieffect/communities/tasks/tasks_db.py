from __future__ import annotations

from datetime import datetime
from typing import Self

from flask_fullstack import Identifiable, TypeEnum
from pydantic_marshals.base import PatchDefault
from pydantic_marshals.sqlalchemy import MappedModel
from sqlalchemy import ForeignKey, select, or_
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.sqltypes import String, Text

from common import db
from common.abstract import FileEmbed, SoftDeletable
from vault.files_db import File

TASKS_PER_PAGE: int = 48


class TaskEmbed(FileEmbed):
    __tablename__ = "cs_embeds"

    task_id: Mapped[int] = mapped_column(
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
    __tablename__ = "cs_tasks"
    not_found_text = "Task not found"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
    )
    user = relationship("User", passive_deletes=True)

    community_id: Mapped[int] = mapped_column(
        ForeignKey("community.id", ondelete="CASCADE"),
    )
    community = relationship("Community", passive_deletes=True)

    # TODO recheck the argument name after information pages will be added
    page_id: Mapped[int] = mapped_column()
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)

    created: Mapped[datetime] = mapped_column(default=datetime.utcnow, index=True)
    opened: Mapped[datetime | None] = mapped_column(index=True)
    closed: Mapped[datetime | None] = mapped_column(index=True)

    files: Mapped[list[File]] = relationship(
        secondary=TaskEmbed.__table__,
        passive_deletes=True,
    )

    @property
    def username(self) -> str:
        return self.user.username

    CreateModel = MappedModel.create(
        columns=[page_id, name, description, opened, closed],
    )
    UpdateModel = CreateModel.as_patch()
    IndexModel = CreateModel.extend(columns=[id, created], properties=[username])
    FullModel = IndexModel.extend(relationships=[(files, File.FullModel)])

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
            if value is not PatchDefault and hasattr(self, key):
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
