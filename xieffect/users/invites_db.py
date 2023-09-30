from __future__ import annotations

from os import getenv
from typing import Self

from flask_fullstack import PydanticModel
from itsdangerous.url_safe import URLSafeSerializer
from sqlalchemy import Column, select
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import Integer, String

from common import Base, db


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
    invited = relationship(
        "User",
        back_populates="invite",
        passive_deletes=True,
    )

    IDModel = PydanticModel.column_model(id)
    IndexModel = PydanticModel.column_model(name, code, limit, accepted)

    @classmethod
    def create(cls, **kwargs) -> Self:
        entry = super().create(**kwargs)
        entry.code = entry.generate_code(0)
        db.session.flush()
        return entry

    @classmethod
    def find_by_id(cls, entry_id: int) -> Self | None:
        return db.get_first(select(cls).filter(cls.id == entry_id))

    @classmethod
    def find_by_code(cls, code: str) -> Self | None:
        return cls.find_by_id(cls.serializer.loads(code)[0])

    @classmethod
    def find_global(cls, offset: int, limit: int) -> list[Self]:
        return db.get_paginated(select(cls), offset, limit)

    def generate_code(self, user_id: int) -> str | bytes:
        return self.serializer.dumps((self.id, user_id))
