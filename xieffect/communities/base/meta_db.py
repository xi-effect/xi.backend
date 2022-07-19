from __future__ import annotations

from sqlalchemy import Column, ForeignKey, select
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import Integer, String, Text, Enum

from common import Identifiable, TypeEnum, PydanticModel, User, Base, sessionmaker


class Community(Base, Identifiable):
    __tablename__ = "community"
    not_found_text = "Community not found"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    invite_count = Column(Integer, nullable=False, default=0)

    participants = relationship("Participant", cascade="all, delete, delete-orphan")

    BaseModel = PydanticModel.column_model(id)
    CreateModel = PydanticModel.column_model(name, description)
    IndexModel = BaseModel.combine_with(CreateModel)

    @classmethod
    def create(cls, session: sessionmaker, name: str, description: str | None, creator: User) -> Community:
        entry: cls = super().create(session, name=name, description=description)

        participant = Participant(user=creator, role=ParticipantRole.OWNER)
        entry.participants.append(participant)
        session.add(participant)
        session.flush()

        return entry

    @classmethod
    def find_by_id(cls, session: sessionmaker, entry_id: int) -> Community | None:
        return session.get_first(select(cls).filter_by(id=entry_id))

    @classmethod
    def find_by_user(cls, session: sessionmaker, user: User, offset: int, limit: int) -> list[Community]:
        ids = session.get_paginated(select(Participant.community_id).filter_by(user_id=user.id), offset, limit)
        return session.get_all(select(cls).filter(cls.id.in_(ids)))


class ParticipantRole(TypeEnum):
    BASE = 0
    OWNER = 4


class Participant(Base):
    __tablename__ = "community_participant"

    community_id = Column(Integer, ForeignKey(Community.id), primary_key=True)
    user_id = Column(Integer, ForeignKey(User.id), primary_key=True)
    user = relationship("User")

    role = Column(Enum(ParticipantRole), nullable=False)

    @classmethod
    def create(cls, session: sessionmaker, community_id: int, user_id: int, role: ParticipantRole):
        return super().create(session, community_id=community_id, user_id=user_id, role=role)

    @classmethod
    def find_by_ids(cls, session: sessionmaker, community_id: int, user_id: int) -> Participant | None:
        return session.get_first(select(cls).filter_by(community_id=community_id, user_id=user_id))
