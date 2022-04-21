from __future__ import annotations

from datetime import datetime, timedelta

from itsdangerous import URLSafeSerializer
from sqlalchemy import Column, select, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import Integer, DateTime, String, Enum

from common import PydanticModel, Identifiable, Base, sessionmaker, app
from .meta_db import Community, ParticipantRole


class Invitation(Base, Identifiable):
    __tablename__ = "community_invites"
    serializer: URLSafeSerializer = URLSafeSerializer(app.config["SECURITY_PASSWORD_SALT"])

    id = Column(Integer, primary_key=True)
    code = Column(String(100), default="")

    community_id = Column(Integer, ForeignKey(Community.id), nullable=False)
    community = relationship("Community")

    role = Column(Enum(ParticipantRole), nullable=False)
    deadline = Column(DateTime, nullable=True)
    limit = Column(Integer, nullable=True)

    BaseModel = PydanticModel.column_model(id, code)
    IndexModel = BaseModel.column_model(role, deadline, limit)

    @classmethod
    def create(cls, session: sessionmaker, community_id: int, role: ParticipantRole, limit: int | None,
               days_to_live: int | None) -> Invitation:
        deadline = None if days_to_live is None else datetime.utcnow() + timedelta(days=days_to_live)
        entry: cls = super().create(session, role=role, community_id=community_id, limit=limit, deadline=deadline)
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
        return self.serializer.dumps((self.community_id, self.id))

    def is_available(self, date: DateTime):
        return self.count_limit != 0 and self.time_limit > date
