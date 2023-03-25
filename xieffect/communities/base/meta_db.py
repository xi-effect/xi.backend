from __future__ import annotations

from flask_fullstack import Identifiable, PydanticModel
from sqlalchemy import Column, ForeignKey, select
from sqlalchemy.orm import relationship, selectinload
from sqlalchemy.sql.sqltypes import Integer, String, Text

from common import User, Base, db
from .roles_db import ParticipantRole, Role


class Community(Base, Identifiable):
    __tablename__ = "community"
    not_found_text = "Community not found"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    invite_count = Column(Integer, nullable=False, default=0)

    participants = relationship("Participant", cascade="all, delete, delete-orphan")

    BaseModel = PydanticModel.column_model(id)
    CreateModel = PydanticModel.column_model(name, description)
    IndexModel = BaseModel.combine_with(CreateModel)

    @classmethod
    def create(cls, name: str, description: str | None, creator: User) -> Community:
        entry: cls = super().create(name=name, description=description)

        participant = Participant(user=creator)
        entry.participants.append(participant)
        db.session.add(participant)
        db.session.flush()

        return entry

    @classmethod
    def find_by_id(cls, entry_id: int) -> Community | None:
        return db.session.get_first(select(cls).filter_by(id=entry_id))


class Participant(Base, Identifiable):
    __tablename__ = "community_participant"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey(User.id), nullable=False)
    community_id = Column(Integer, ForeignKey(Community.id), nullable=False)
    user = relationship("User")
    roles = relationship("Role", secondary=ParticipantRole.__table__)

    UpdateModel = PydanticModel.column_model(community_id)
    FullModel = (
        PydanticModel.column_model(id, user_id)
        .combine_with(UpdateModel)
        .nest_model(Role.IndexModel, "roles", as_list=True)
    )

    @classmethod
    def create(cls, community_id: int, user_id: int):
        return super().create(
            community_id=community_id,
            user_id=user_id,
        )

    @classmethod
    def find_by_id(cls, participant_id: int) -> Role | None:
        return db.session.get_first(select(cls).filter_by(id=participant_id))

    @classmethod
    def find_by_ids(cls, community_id: int, user_id: int) -> Participant | None:
        return db.session.get_first(
            select(cls).filter_by(community_id=community_id, user_id=user_id)
        )

    @classmethod
    def search_by_username(
        cls,
        search: str,
        offset: int,
        limit: int,
    ) -> list[Participant]:
        stmt = select(cls).options(selectinload(cls.roles))
        if len(search) == 0:
            return db.session.get_paginated(stmt, offset, limit)
        return db.session.get_paginated(
            stmt.join(User, User.id == cls.id).where(
                User.username.ilike(f"%{search}%")
            ),
            offset,
            limit,
        )
