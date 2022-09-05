from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, ForeignKey, select, update
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import Boolean, DateTime, Integer, String, Text

from common import Base, Identifiable, PydanticModel
from vault.files_db import File


class TaskEmbed(Base):
    __tablename__ = "cs_embeds"

    task_id = Column(Integer, ForeignKey("cs_tasks.id"), primary_key=True)
    file_id = Column(Integer, ForeignKey("files.id"), primary_key=True)
    file = relationship("File")

    FileModel = PydanticModel.nest_flat_model(File.FullModel, "file")

    @classmethod
    def add_files(cls, session, task_id: int, file_ids: list[int]) -> None:
        for file_id in file_ids:
            cls.create(session, task_id=task_id, file_id=file_id)

    @classmethod
    def delete_files(cls, session, task_id: int, file_ids: list[int]) -> None:
        for file_id in file_ids:
            session.delete(
                cls.find_first_by_kwargs(session, task_id=task_id, file_id=file_id)
            )

    @classmethod
    def get_task_files(cls, session, task_id: int) -> list[int]:
        stmt = select(cls.file_id).filter_by(task_id=task_id)
        return session.get_all(stmt)


class Task(Base, Identifiable):
    __tablename__ = "cs_tasks"
    not_found_text = "Task not found"

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user = relationship("User")

    community_id = Column(Integer, ForeignKey("community.id"), nullable=False)
    community = relationship("Community")

    # TODO recheck the argument name after information pages will be added
    page_id = Column(Integer, nullable=False)  # ForeignKey("page_table.id")
    # page = relationship("Page_table")

    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    created = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    deleted = Column(Boolean, nullable=False, default=False)

    files = relationship("TaskEmbed")

    BaseModel = PydanticModel.column_model(
        id,
        name,
        description,
        updated,
    )

    class IndexModel(BaseModel):
        username: str

        @classmethod
        def callback_convert(cls, callback, orm_object: Task, **context) -> None:
            callback(username=orm_object.user.username)

    FullModel = IndexModel.nest_model(TaskEmbed.FileModel, "files", as_list=True)

    @classmethod
    def find_by_id(cls, session, task_id: int) -> Task | None:
        """Find only not deleted task (deleted=False)"""
        return session.get_first(select(cls).filter_by(id=task_id, deleted=False))

    @classmethod
    def create(
        cls,
        session,
        user_id: int,
        community_id: int,
        page_id: int,
        name: str,
        description: str,
    ) -> Task:
        return super().create(
            session,
            user_id=user_id,
            community_id=community_id,
            page_id=page_id,
            name=name,
            description=description,
        )

    @classmethod
    def update(cls, session, task_id: int, community_id: int, **kwargs) -> None:
        session.execute(
            update(cls)
            .where(cls.id == task_id, cls.community_id == community_id)
            .values(**kwargs)
        )
