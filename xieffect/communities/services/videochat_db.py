from __future__ import annotations

from flask_fullstack import PydanticModel, Identifiable
from sqlalchemy import Column, ForeignKey, JSON, select
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import relationship
from sqlalchemy.sql.functions import count
from sqlalchemy.sql.sqltypes import Integer, Text

from common import db, Base, User

PARTICIPANT_LIMIT: int = 50


class ChatParticipant(Base):  # TODO community to room after channels creating
    __tablename__ = "cs_chat_participants"

    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    community_id = Column(
        Integer, ForeignKey("community.id", ondelete="CASCADE"), primary_key=True
    )
    state = Column(MutableDict.as_mutable(JSON), nullable=False)

    CreateModel = PydanticModel.column_model(community_id, state)
    IndexModel = CreateModel.column_model(user_id)

    @classmethod
    def create(cls, user_id: int, community_id: int, state: dict) -> ChatParticipant:
        return super().create(
            user_id=user_id,
            community_id=community_id,
            state=state,
        )

    @classmethod
    def find_by_ids(
        cls, user_id: int, community_id: int
    ) -> ChatParticipant | None:
        return db.session.get_first(
            select(cls).filter_by(user_id=user_id, community_id=community_id)
        )

    @classmethod
    def find_by_community(cls, community_id: int) -> list[ChatParticipant]:
        return db.session.get_all(select(cls).filter_by(community_id=community_id))

    @classmethod
    def get_count_by_community(cls, community_id: int) -> int:
        return db.session.get_first(
            select(count(cls.user_id)).filter_by(community_id=community_id)
        )


class ChatMessage(Base, Identifiable):  # TODO community to room after channels creating
    __tablename__ = "cs_chat_messages"
    not_found_text = "Message not found"

    id = Column(Integer, primary_key=True)
    content = Column(Text, nullable=False)

    community_id = Column(
        Integer, ForeignKey("community.id", ondelete="CASCADE"), nullable=False
    )
    sender_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    sender: User | relationship = relationship("User")

    CreateModel = PydanticModel.column_model(content)
    IndexModel = (
        CreateModel.column_model(id)
        .nest_model(User.MainData, "sender")
    )

    @classmethod
    def create(cls, sender: User, community_id: int, content: str) -> ChatMessage:
        return super().create(
            sender=sender,
            community_id=community_id,
            content=content,
        )

    @classmethod
    def find_by_id(cls, entry_id: int) -> ChatMessage | None:
        return db.session.get_first(select(cls).filter_by(id=entry_id))

    @classmethod
    def find_by_ids(
        cls, community_id: int, offset: int, limit: int
    ) -> list[ChatMessage]:
        stmt = select(cls).filter_by(community_id=community_id)
        return db.session.get_paginated(stmt, offset, limit)
