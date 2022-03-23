from __future__ import annotations

from os import getenv
from typing import Union

from itsdangerous.url_safe import URLSafeSerializer
from sqlalchemy import Column, select
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import Integer, String

from common import create_marshal_model, Marshalable, Base, sessionmaker


@create_marshal_model("invite", "name", "code", "limit", "accepted")
class Invite(Base, Marshalable):
    __tablename__ = "invites"
    not_found_text = "Invite not found"
    serializer: URLSafeSerializer = URLSafeSerializer(getenv("SECRET_KEY", "local"))  # TODO redo

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    code = Column(String(100), nullable=False, default="")
    limit = Column(Integer, nullable=False, default=-1)
    accepted = Column(Integer, nullable=False, default=0)
    invited = relationship("User", back_populates="invite")

    @classmethod
    def create(cls, session: sessionmaker, name: str, limit: int = -1) -> Invite:
        entry: cls = cls(name=name, limit=limit)  # noqa
        session.add(entry)
        session.flush()
        entry.code = entry.generate_code(0)
        session.flush()
        return entry

    @classmethod
    def find_by_id(cls, session: sessionmaker, entry_id: int) -> Union[Invite, None]:
        return session.execute(select(cls).filter(cls.id == entry_id)).scalars().first()

    @classmethod
    def find_by_code(cls, session: sessionmaker, code: str) -> Union[Invite, None]:
        return cls.find_by_id(session, cls.serializer.loads(code)[0])

    @classmethod
    def find_global(cls, session: sessionmaker, offset: int, limit: int) -> list[Invite]:
        return session.execute(select(cls).offset(offset).limit(limit)).scalars().all()

    def generate_code(self, user_id: int):
        return self.serializer.dumps((self.id, user_id))

    def delete(self, session: sessionmaker):
        session.delete(self)
        session.flush()
