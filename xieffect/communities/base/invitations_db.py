from __future__ import annotations

from datetime import datetime, timedelta

from flask_fullstack import PydanticModel, Identifiable
from itsdangerous import URLSafeSerializer
from sqlalchemy import Column, select, ForeignKey
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql.sqltypes import Integer, DateTime, String

from common import Base, db, app
from .meta_db import Community


class Invitation(Base, Identifiable):
    __tablename__ = "community_invites"
    serializer: URLSafeSerializer = URLSafeSerializer(
        app.config["SECURITY_PASSWORD_SALT"]
    )

    id = Column(Integer, primary_key=True)
    code = Column(String(100), default="")

    community_id = Column(Integer, ForeignKey(Community.id), nullable=False)
    community = relationship(
        "Community",
        backref=backref("invitations", cascade="all, delete, delete-orphan"),
    )

    deadline = Column(DateTime, nullable=True)
    limit = Column(Integer, nullable=True)

    BaseModel = PydanticModel.column_model(id, code)
    CreationBaseModel = PydanticModel.column_model(limit)
    IndexModel = BaseModel.column_model(deadline).combine_with(CreationBaseModel)

    @classmethod
    def create(
        cls,
        community_id: int,
        limit: int | None,
        days_to_live: int | None,
    ) -> Invitation:
        entry: cls = super().create(
            community_id=community_id,
            limit=limit,
            deadline=(
                None
                if days_to_live is None
                else datetime.utcnow() + timedelta(days=days_to_live)
            ),
        )
        entry.code = entry.generate_code()
        db.session.flush()
        return entry

    @classmethod
    def find_by_id(cls, invitation_id: int) -> Invitation | None:
        return db.session.get_first(select(cls).filter_by(id=invitation_id))

    @classmethod
    def find_by_community(
        cls, community_id: int, offset: int, limit: int
    ) -> list[Invitation]:
        return db.session.get_paginated(
            select(cls).filter_by(community_id=community_id), offset, limit
        )

    @classmethod
    def find_by_code(cls, code: str) -> Invitation | None:
        return db.session.get_first(select(cls).filter_by(code=code))

    def generate_code(self):
        return self.serializer.dumps((self.community_id, self.id))

    def has_valid_deadline(self) -> bool:
        return self.deadline is None or self.deadline >= datetime.utcnow()

    def is_invalid(self) -> bool:
        return not self.has_valid_deadline() or self.limit == 0
