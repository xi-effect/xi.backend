from __future__ import annotations
from typing import Union
from itsdangerous import URLSafeSerializer
from sqlalchemy import Column, select, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import Integer, DateTime, String

from common import Marshalable, create_marshal_model, Identifiable
from main import Base, Session, app
from .meta_db import Community
from datetime import datetime


@create_marshal_model("invitation-base", "community_id", "time_limit", "code", "role", "count_limit")
class Invitation(Base, Identifiable, Marshalable):
    __tablename__ = "community_invites"
    serializer: URLSafeSerializer = URLSafeSerializer(app.config["SECURITY_PASSWORD_SALT"])

    invitation_id = Column(Integer, primary_key=True)

    community_id = Column(Integer, ForeignKey(Community.id), nullable=False)
    community = relationship("Community")

    time_limit = Column(DateTime, default=datetime.now().date())
    code = Column(String(100), default='')
    role = Column(Integer, default=1)
    count_limit = Column(Integer, nullable=False, default=-1)

    @classmethod
    def create(cls, session: Session, community_id: int, role: int = 1, count_limit: int = -1,
               time_limit: DateTime = datetime.now()) -> Invitation:
        entry: cls = cls(role=role, count_limit=count_limit, community=Community.find_by_id(session, community_id),
                         time_limit=time_limit)
        session.add(entry)
        session.flush()
        entry.code = entry.generate_code()
        session.flush()
        return entry

    @classmethod
    def find_by_id(cls, session: Session, invitation_id: int) -> Union[Invitation, None]:
        return session.execute(select(cls).filter_by(invitation_id=invitation_id)).scalars().first()

    @classmethod
    def find_invitation_by_community_id(cls, session: Session, community_id: int, offset: int, limit: int) -> list[Invitation]:
        query = session.execute(select(cls).filter(cls.community_id == community_id).offset(offset).limit(limit)).scalars().all()
        return query

    @classmethod
    def find_community_by_id(cls, session: Session, community_id: int) -> Union[Community, None]:
        return Community.find_by_id(session, community_id)

    @classmethod
    def get_invitation_by_url(cls, session: Session, url: str):
        return session.execute(select(cls).filter_by(code=url)).scalars().first()

    def generate_code(self):
        return self.serializer.dumps(([self.community_id, self.invitation_id]))

    def get_code(self):
        return self.code

    def delete(self, session):
        session.delete(self)
        session.flush()
