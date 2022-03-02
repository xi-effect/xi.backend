from __future__ import annotations

from itsdangerous import URLSafeSerializer
from sqlalchemy import Column
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import Integer, DateTime

from common import Marshalable, create_marshal_model
from main import Base, Session, app
from .meta_db import Community
from datetime import datetime


@create_marshal_model("community_invites", "role", "code", "limit", "time_limit")
class Invitations(Base, Marshalable):
    __tablename__ = "community_invites"
    serializer: URLSafeSerializer = URLSafeSerializer(app.config["SECURITY_PASSWORD_SALT"])

    invite_id = Column(Integer, primary_key=True)
    time_limit = Column(DateTime, default=datetime.now())
    role = Column(Integer, default=1)
    count_limit = Column(Integer, nullable=False, default=-1)
    community = relationship("Community")

    @classmethod
    def create(cls, session: Session, community: Community, role: int = 1, count_limit: int = -1, time_limit: int = datetime.now()) -> Invitations:
        entry: cls = cls(role=role, count_limit=count_limit, community=community, time_limit=time_limit)
        session.add(entry)
        session.flush()
        return entry

    def delete(self, session):
        session.delite(self)
        session.flush()
