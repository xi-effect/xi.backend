from __future__ import annotations

from datetime import datetime, timedelta

from itsdangerous import URLSafeSerializer
from sqlalchemy import Column, select, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import Integer, DateTime, String, Enum

from common import Marshalable, create_marshal_model, Identifiable, Base, sessionmaker, app
from .meta_db import Community, ParticipantRole


@create_marshal_model("invitation-index", "role", "deadline", "limit", inherit="invitation-base")
@create_marshal_model("invitation-base", "id", "code")
class Invitation(Base, Identifiable, Marshalable):
    __tablename__ = "community_invites"
    serializer: URLSafeSerializer = URLSafeSerializer(app.config["SECURITY_PASSWORD_SALT"])

    id = Column(Integer, primary_key=True)
    code = Column(String(100), default="")

    community_id = Column(Integer, ForeignKey(Community.id), nullable=False)
    community = relationship("Community")

    role = Column(Enum(ParticipantRole), nullable=False)
    deadline = Column(DateTime, nullable=True)
    limit = Column(Integer, nullable=True)

    @classmethod
    def create(cls, session: sessionmaker, community_id: int, role: ParticipantRole, limit: int | None,
               days_to_live: int | None) -> Invitation:
        entry: cls = super().create(session, role=role, community_id=community_id, limit=limit,
                                    deadline=datetime.utcnow() + timedelta(days=days_to_live))
        entry.code = entry.generate_code()
        session.flush()
        return entry

    @classmethod
    def find_by_id(cls, session: sessionmaker, invitation_id: int) -> Invitation | None:
        return session.get_first(select(cls).filter_by(id=invitation_id))

    @classmethod
    def find_by_community(cls, session: sessionmaker, community_id: int, offset: int, limit: int) -> list[Invitation]:
        return session.get_paginated(select(cls).filter_by(community_id=community_id), offset, limit)

    @classmethod
    def find_by_code(cls, session: sessionmaker, code: str) -> Invitation | None:
        return session.get_first(select(cls).filter_by(code=code))

    def generate_code(self):
        return self.serializer.dumps((self.community_id, self.invitation_id))

    def is_available(self, date: DateTime):
        return self.count_limit != 0 and self.time_limit > date
