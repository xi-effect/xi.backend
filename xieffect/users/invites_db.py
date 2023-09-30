from __future__ import annotations

from os import getenv
from typing import Self, ClassVar

from itsdangerous.url_safe import URLSafeSerializer
from pydantic_marshals.sqlalchemy import MappedModel
from sqlalchemy import select
from sqlalchemy.orm import relationship, mapped_column
from sqlalchemy.sql.sqltypes import Integer, String

from common import Base, db
from common.pydantic import v2_model_to_ffs
from common.users_db import Mapped


class Invite(Base):
    __tablename__ = "invites"
    not_found_text = "Invite not found"
    serializer: ClassVar[URLSafeSerializer] = URLSafeSerializer(
        getenv("SECRET_KEY", "local")
    )  # TODO redo

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    code: Mapped[str] = mapped_column(String(100), default="")
    limit: Mapped[int] = mapped_column(Integer, default=-1)
    accepted: Mapped[int] = mapped_column(Integer, default=0)
    invited = relationship(
        "User",
        back_populates="invite",
        passive_deletes=True,
    )

    IDModel = MappedModel.create(columns=[id])
    IndexModel = MappedModel.create(columns=[name, code, limit, accepted])

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


Invite.IDModel = v2_model_to_ffs(Invite.IDModel)
Invite.IndexModel = v2_model_to_ffs(Invite.IndexModel)
