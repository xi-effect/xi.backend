from __future__ import annotations

from typing import Self

from flask_fullstack import PydanticModel, Identifiable
from sqlalchemy import Column, ForeignKey
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import Integer, JSON, Boolean

from common import Base
from common.abstract import FileEmbed
from vault.files_db import File


class MessageFile(FileEmbed):
    __tablename__ = "ds_message_files"

    message_id = Column(
        Integer,
        ForeignKey("ds_messages.id", ondelete="CASCADE", onupdate="CASCADE"),
        primary_key=True,
    )


class DiscussionMessage(Base, Identifiable):
    __tablename__ = "ds_messages"

    id = Column(Integer, primary_key=True)
    content = Column(MutableDict.as_mutable(JSON), nullable=False)
    pinned = Column(Boolean, default=False, nullable=False)
    # system = Column(Enum(?), nullable=False)  # TODO: Type of system message

    sender_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
    )
    sender = relationship("User")

    discussion_id = Column(
        Integer,
        ForeignKey(
            "discussions.id",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        nullable=False,
    )
    discussion = relationship("Discussion")

    files = relationship("File", secondary=MessageFile.__table__, passive_deletes=True)

    CreateModel = PydanticModel.column_model(content, sender_id, discussion_id)
    IndexModel = CreateModel.nest_model(File.FullModel, "files", as_list=True)

    @classmethod
    def create(
        cls,
        content: dict,
        sender_id: int,
        discussion_id: int,
        files: list[int] | None = None,
    ) -> Self:
        message: Self = super().create(
            content=content,
            sender_id=sender_id,
            discussion_id=discussion_id,
        )
        MessageFile.add_files(set(files or []), message_id=message.id)
        return message

    @classmethod
    def find_by_id(cls, entry_id: int) -> Self | None:
        return cls.find_first_by_kwargs(id=entry_id)

    def update(self, content: dict | None, files: list[int] | None) -> None:
        if content is not None:
            self.content = content
        if files is not None:
            old_files: set[int] = set(MessageFile.get_file_ids(message_id=self.id))
            MessageFile.delete_files(old_files - set(files), message_id=self.id)
            MessageFile.add_files(set(files) - old_files, message_id=self.id)


class Discussion(Base, Identifiable):
    __tablename__ = "discussions"

    id = Column(Integer, primary_key=True)
    messages = relationship(
        "DiscussionMessage",
        back_populates="discussion",
        cascade="all, delete",
        passive_deletes=True,
    )

    IndexModel = PydanticModel.column_model(id).nest_model(
        DiscussionMessage.IndexModel, "messages", as_list=True
    )

    @classmethod
    def find_by_id(cls, entry_id: int) -> Self | None:
        return cls.find_first_by_kwargs(id=entry_id)

    @classmethod
    def get_discussion(
        cls, entry_id: int, offset: int = 0, limit: int = 50
    ) -> list[Self]:
        return cls.find_paginated_by_kwargs(offset, limit, id=entry_id)
