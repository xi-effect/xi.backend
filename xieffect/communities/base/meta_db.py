from __future__ import annotations

from typing import Union

from sqlalchemy import Column, ForeignKey, select
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import Integer, String, Text, Enum

from common import Identifiable, TypeEnum, create_marshal_model, Marshalable, User
from main import Base, Session


@create_marshal_model("community-base", "name", "description")
class Community(Base, Identifiable, Marshalable):
    __tablename__ = "community"
    not_found_text = "Community not found"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    invite_count = Column(Integer, nullable=False, default=0)

    participants = relationship("Participant", cascade="all, delete")

    @classmethod
    def create(cls, session: Session, name: str, description: str, creator: User) -> Community:
        entry: cls = cls(name=name, description=description)
        session.add(entry)
        session.flush()

        participant = Participant(user=creator, role=ParticipantRole.OWNER)
        entry.participants.append(participant)
        session.add(participant)
        session.flush()

        return entry

    @classmethod
    def find_by_id(cls, session: Session, entry_id: int) -> Union[Community, None]:
        return session.execute(select(cls).filter_by(id=entry_id)).scalars().first()

    @classmethod
    def find_by_user(cls, session: Session, user: User, offset: int, limit: int) -> list[Community]:
        ids = session.execute(select(Participant.community_id).filter_by(user_id=user.id).offset(offset).limit(limit))
        return session.execute(select(cls).filter(cls.id.in_(ids.scalars().all()))).scalars().all()


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
    def create(cls, session: Session, community_id: int, user_id: int):
        entry: cls = cls(community_id=community_id, user_id=user_id, role=ParticipantRole.BASE)
        session.add(entry)
        session.flush()

        return entry

    @classmethod
    def find_by_ids(cls, session: Session, community_id: int, user_id: int) -> Union[Participant, None]:
        return session.execute(select(cls).filter_by(community_id=community_id, user_id=user_id)).scalars().first()
