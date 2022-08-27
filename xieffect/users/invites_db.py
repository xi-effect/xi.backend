from __future__ import annotations

from os import getenv
from typing import Union

from itsdangerous.url_safe import URLSafeSerializer
from sqlalchemy import Column, select
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import Integer, String

from common import Base, sessionmaker, PydanticModel


class Invite(Base):
    __tablename__ = "invites"
    not_found_text = "Invite not found"
    serializer: URLSafeSerializer = URLSafeSerializer(
        getenv("SECRET_KEY", "local")
    )  # TODO redo

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    code = Column(String(100), nullable=False, default="")
    limit = Column(Integer, nullable=False, default=-1)
    accepted = Column(Integer, nullable=False, default=0)
    invited = relationship("User", back_populates="invite")

    IndexModel = PydanticModel.column_model(name, code, limit, accepted)

    @classmethod
    def create(cls, session: sessionmaker, **kwargs) -> Invite:
        entry = super().create(session, **kwargs)
        entry.code = entry.generate_code(0)
        session.flush()
        return entry

    @classmethod
    def find_by_id(cls, session: sessionmaker, entry_id: int) -> Union[Invite, None]:
        return session.get_first(select(cls).filter(cls.id == entry_id))

    @classmethod
    def find_by_code(cls, session: sessionmaker, code: str) -> Union[Invite, None]:
        return cls.find_by_id(session, cls.serializer.loads(code)[0])

    @classmethod
    def find_global(
        cls, session: sessionmaker, offset: int, limit: int
    ) -> list[Invite]:
        return session.get_paginated(select(cls), offset, limit)

    def generate_code(self, user_id: int):
        return self.serializer.dumps((self.id, user_id))
