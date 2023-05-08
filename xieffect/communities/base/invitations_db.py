from __future__ import annotations

from datetime import datetime, timedelta
from typing import Self

from flask_fullstack import PydanticModel, Identifiable
from itsdangerous import URLSafeSerializer
from sqlalchemy import Column, select, ForeignKey
from sqlalchemy.orm import relationship, selectinload
from sqlalchemy.sql.sqltypes import Integer, DateTime, String

from common import Base, db, app
from .meta_db import Community
from .roles_db import Role


class InvitationRoles(Base):
    __tablename__ = "cs_invitation_roles"

    invitation_id = Column(
        Integer, ForeignKey("cs_invitations.id", ondelete="CASCADE"), primary_key=True
    )
    role_id = Column(
        Integer, ForeignKey("cs_roles.id", ondelete="CASCADE"), primary_key=True
    )

    @classmethod
    def create_bulk(cls, invitation_id: int, role_ids: list[int]) -> None:
        db.session.add_all(
            cls(invitation_id=invitation_id, role_id=role_id) for role_id in role_ids
        )
        db.session.flush()


class Invitation(Base, Identifiable):
    __tablename__ = "cs_invitations"
    serializer: URLSafeSerializer = URLSafeSerializer(
        app.config["SECURITY_PASSWORD_SALT"]
    )

    id = Column(Integer, primary_key=True)
    code = Column(String(100), default="")

    community_id = Column(
        Integer,
        ForeignKey(Community.id, ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    community = relationship("Community")

    roles = relationship("Role", secondary=InvitationRoles.__table__)
    deadline = Column(DateTime, nullable=True)
    limit = Column(Integer, nullable=True)

    CreationBaseModel = PydanticModel.column_model(limit)
    FullModel = (
        PydanticModel.column_model(id, code, deadline)
        .combine_with(CreationBaseModel)
        .nest_model(Role.IndexModel, "roles", as_list=True)
    )

    @classmethod
    def create(
        cls,
        community_id: int,
        limit: int | None,
        days_to_live: int | None,
    ) -> Self:
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
    def find_by_id(cls, invitation_id: int) -> Self | None:
        return db.get_first(select(cls).filter_by(id=invitation_id))

    @classmethod
    def find_by_community(
        cls, community_id: int, offset: int, limit: int
    ) -> list[Self]:
        return db.get_paginated(
            select(cls)
            .options(selectinload(cls.roles))
            .filter_by(community_id=community_id),
            offset,
            limit,
        )

    @classmethod
    def find_by_code(cls, code: str) -> Self | None:
        return db.get_first(select(cls).filter_by(code=code))

    def generate_code(self) -> str | bytes:
        return self.serializer.dumps((self.community_id, self.id))

    def has_valid_deadline(self) -> bool:
        return self.deadline is None or self.deadline >= datetime.utcnow()

    def is_invalid(self) -> bool:
        return not self.has_valid_deadline() or self.limit == 0
