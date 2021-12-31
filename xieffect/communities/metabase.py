from __future__ import annotations

from collections.abc import Sequence
from typing import Union

from itsdangerous import URLSafeSerializer
from sqlalchemy import Column, ForeignKey, select
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import Integer, String, Text, Enum

from componets import Identifiable, TypeEnum, create_marshal_model, Marshalable
from main import Base, Session, app
from users import User


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


class Invite(Base, Marshalable):
    __tablename__ = "community_invites"
    serializer: URLSafeSerializer = URLSafeSerializer(app.config["SECURITY_PASSWORD_SALT"])

    community = relationship("Community")
    community_id = Column(Integer, ForeignKey(Community.id), primary_key=True)
    invite_id = Column(Integer, primary_key=True)
    code = Column(String(100), nullable=False, default="")

    role = Column(Enum(ParticipantRole), nullable=False)
    limit = Column(Integer, nullable=False, default=-1)
    accepted = Column(Integer, nullable=False, default=0)

    @classmethod
    def create(cls, session: Session, community: Community, role: ParticipantRole, limit: int = -1) -> Invite:
        entry: cls = cls(role=role, limit=limit, community=community, invite_id=community.invite_count)  # noqa
        community.invite_count += 1
        session.add(entry)
        session.flush()
        entry.code = entry.generate_code()
        session.flush()
        return entry

    @classmethod
    def find_by_ids(cls, session: Session, community_id: int, invite_id: int) -> Union[Invite, None]:
        return session.execute(select(cls).filter_by(community_id=community_id, invite_id=invite_id)).scalars().first()

    @classmethod
    def find_by_code(cls, session: Session, code: str) -> Union[Invite, None]:
        temp = cls.serializer.loads(code)
        if not isinstance(temp, Sequence) or len(temp) != 2:
            raise TypeError
        community_id, invite_id = temp
        if not isinstance(community_id, int) or not isinstance(invite_id, int):
            raise TypeError
        return cls.find_by_ids(session, community_id, invite_id)

    def generate_code(self):
        return self.serializer.dumps((self.community_id, self.invite_id))
