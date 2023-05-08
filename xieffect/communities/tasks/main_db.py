from __future__ import annotations

from datetime import datetime
from typing import Self

from flask_fullstack import Identifiable, PydanticModel, TypeEnum
from sqlalchemy import Column, ForeignKey, select, update, delete, or_
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import DateTime, Integer, String, Text

from common import Base, db
from common.abstract import SoftDeletable
from communities.base.meta_db import Participant, ParticipantRole
from vault.files_db import File

TASKS_PER_PAGE: int = 48


class TaskEmbed(Base):
    __tablename__ = "cs_embeds"

    task_id = Column(
        Integer,
        ForeignKey("cs_tasks.id", ondelete="CASCADE", onupdate="CASCADE"),
        primary_key=True,
    )
    file_id = Column(
        Integer,
        ForeignKey("files.id", ondelete="CASCADE", onupdate="CASCADE"),
        primary_key=True,
    )
    file = relationship("File")

    FileModel = PydanticModel.nest_flat_model(File.FullModel, "file")

    @classmethod
    def add_files(cls, task_id: int, file_ids: set[int]) -> None:
        values: list[dict] = [
            {"task_id": task_id, "file_id": file} for file in file_ids
        ]
        db.bulk_insert_mappings(cls, values)

    @classmethod
    def delete_files(cls, task_id: int, file_ids: set[int]) -> None:
        db.session.execute(
            delete(cls).filter(cls.task_id == task_id, cls.file_id.in_(file_ids))
        )

    @classmethod
    def get_task_files(cls, task_id: int) -> list[int]:
        return db.get_all(select(cls.file_id).filter(cls.task_id == task_id))


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

    id = Column(Integer, primary_key=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    user = relationship("User")

    community_id = Column(
        Integer,
        ForeignKey("community.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    community = relationship("Community")

    # TODO recheck the argument name after information pages will be added
    page_id = Column(Integer, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    created = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    opened = Column(DateTime, nullable=True, index=True)
    closed = Column(DateTime, nullable=True, index=True)

    files = relationship("TaskEmbed", passive_deletes=True)

    BaseModel = PydanticModel.column_model(id, created)
    CreateModel = PydanticModel.column_model(page_id, name, description, opened, closed)

    class IndexModel(BaseModel, CreateModel):
        username: str

        @classmethod
        def callback_convert(cls, callback, orm_object: Task, **_) -> None:
            callback(username=orm_object.user.username)

    FullModel = IndexModel.nest_model(TaskEmbed.FileModel, "files", as_list=True)

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
        description: str | None,
        opened: datetime | None,
        closed: datetime | None,
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

    @classmethod
    def update(cls, task_id: int, **kwargs) -> None:
        db.session.execute(update(cls).filter(cls.id == task_id).values(**kwargs))

    @classmethod
    def get_paginated_tasks(
        cls,
        offset: int,
        limit: int,
        participant: Participant,
        entry_filter: TaskFilter,
        entry_order: TaskOrder = TaskOrder.CREATED,
        **kwargs,
    ) -> list[Self]:
        stmt = select(cls).filter_by(**kwargs).order_by(entry_order.name.lower())
        if participant.role == ParticipantRole.BASE:
            stmt.filter(cls.opened <= datetime.utcnow())
        if entry_filter == TaskFilter.ACTIVE:
            stmt = stmt.filter(
                cls.opened <= datetime.utcnow(),
                or_(cls.closed > datetime.utcnow(), cls.closed.is_(None)),
            )
        return db.get_paginated(stmt, offset, limit)
