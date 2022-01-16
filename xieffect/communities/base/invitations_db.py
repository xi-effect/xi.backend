from __future__ import annotations

from collections.abc import Sequence
from typing import Union

from itsdangerous import URLSafeSerializer
from sqlalchemy import Column, ForeignKey, select
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import Integer, String, Enum, DateTime

from common import Marshalable, User, create_marshal_model
from main import Base, Session, app
from .meta_db import Community, Participant, ParticipantRole


@create_marshal_model("community_invites", "role", "code", "limit", "accepted", "time_limit")
class Invite(Base, Marshalable):
    __tablename__ = "community_invites"
    serializer: URLSafeSerializer = URLSafeSerializer(app.config["SECURITY_PASSWORD_SALT"])

    community = relationship("Community")
    community_id = Column(Integer, ForeignKey(Community.id), primary_key=True)
    invite_id = Column(Integer, primary_key=True)
    code = Column(String(100), nullable=False, default="")
    time_limit = (DateTime())
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

    def accept(self, session: Session, acceptor: User) -> bool:
        if Participant.find_by_ids(session, self.community_id, acceptor.id) is not None:
            return False
        participant = Participant(user=acceptor, role=self.role)
        self.community.participants.append(participant)
        session.add(participant)
        session.flush()
        return True

    def generate_code(self):
        return self.serializer.dumps((self.community_id, self.invite_id))

    def delete(self, session):
        session.delite(self)
        session.flush()
