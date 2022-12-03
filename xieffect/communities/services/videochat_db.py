from __future__ import annotations

from flask_fullstack import PydanticModel, Identifiable
from sqlalchemy import Column, ForeignKey, select
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import Integer, Text, Boolean

from common import db, Base, User


PARTICIPANT_LIMIT = 50


class CommunityParticipant(Base):  # TODO community to room after channels creating
    __tablename__ = "participant_to_community"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    user = relationship("User")

    community_id = Column(Integer, ForeignKey("community.id"), primary_key=True)
    community = relationship("Community")

    microphone = Column(Boolean, default=True)
    camera = Column(Boolean, default=True)

    IdModel = PydanticModel.column_model(user_id)
    CreateModel = IdModel.column_model(community_id)
    IndexModel = IdModel.column_model(microphone, camera)

    @classmethod
    def create(cls, user_id: int, community_id: int) -> CommunityParticipant:
        return super().create(user_id=user_id, community_id=community_id)

    @classmethod
    def find_by_ids(
        cls, user_id: int, community_id: int
    ) -> CommunityParticipant | None:
        stmt = select(cls).filter_by(user_id=user_id, community_id=community_id)
        return db.session.get_first(stmt)

    @classmethod
    def find_by_community(cls, community_id: int) -> list[CommunityParticipant]:
        return db.session.get_all(select(cls).filter_by(community_id=community_id))

    def get_by_string(self, target: str) -> bool | None:
        return getattr(self, target, None)

    def set_by_string(self, target: str, state: bool) -> bool | None:
        return setattr(self, target, state)


class CommunityMessage(Base, Identifiable):  # TODO community to room after channels creating
    __tablename__ = "message_to_community"

    id = Column(Integer, primary_key=True)
    text = Column(Text, nullable=False)

    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    creator: User | relationship = relationship("User")

    community_id = Column(Integer, ForeignKey("community.id"))
    community = relationship("Community")

    TextModel = PydanticModel.column_model(text)
    IndexModel = (
        TextModel.column_model(id)
        .nest_model(User.ProfileData, "username", "username")
    )

    @classmethod
    def create(cls, creator: User, community_id: int, text: str) -> CommunityMessage:
        return super().create(creator=creator, community_id=community_id, text=text)

    @classmethod
    def find_by_id(cls, entry_id: int) -> CommunityMessage | None:
        return db.session.get_first(select(cls).filter_by(id=entry_id))

    @classmethod
    def find_by_ids(
        cls, community_id: int, offset: int, limit: int
    ) -> list[CommunityMessage]:
        stmt = select(cls).filter_by(community_id=community_id)
        return db.session.get_paginated(stmt, offset, limit)
