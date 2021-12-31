from __future__ import annotations

from typing import Union

from sqlalchemy import Column, ForeignKey, select
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import Integer, String, Text, Enum

from componets import Identifiable, TypeEnum, create_marshal_model, Marshalable
from main import Base, Session
from users import User


@create_marshal_model("community-base", "name", "description")
class Community(Base, Identifiable, Marshalable):
    __tablename__ = "community"
    not_found_text = "Community not found"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)

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

    def invites(self, session: Session, offset: int, limit: int) -> list[Invite]:
        return session.execute(
            select(Invite).filter_by(community_id=self.id).offset(offset).limit(limit)).scalars().all()


class ParticipantRole(TypeEnum):
    BASE = 0
    OWNER = 4


class Participant(Base):
    __tablename__ = "community_participant"

    community_id = Column(Integer, ForeignKey(Community.id), primary_key=True)
    user_id = Column(Integer, ForeignKey(User.id), primary_key=True)
    user = relationship("User")

    role = Column(Enum(ParticipantRole), nullable=False)
