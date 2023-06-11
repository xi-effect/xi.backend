from __future__ import annotations

from typing import Self

from flask_fullstack import Identifiable, PydanticModel
from sqlalchemy import Column, ForeignKey, select, literal
from sqlalchemy.orm import aliased, relationship, selectinload
from sqlalchemy.sql.sqltypes import Integer, String, Text

from common import User, db
from common.abstract import SoftDeletable, LinkedListNode
from vault.files_db import File
from .roles_db import ParticipantRole, Role


class Community(SoftDeletable, Identifiable):
    __tablename__ = "community"
    not_found_text = "Community not found"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    invite_count = Column(Integer, nullable=False, default=0)

    avatar_id = Column(
        Integer,
        ForeignKey("files.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
    )
    avatar = relationship("File", foreign_keys=[avatar_id])

    owner_id = Column(
        Integer, ForeignKey(User.id, ondelete="CASCADE"), nullable=False
    )  # TODO ondelete is temporary

    participants = relationship("Participant", passive_deletes=True)

    CreateModel = PydanticModel.column_model(name, description)
    IndexModel = CreateModel.column_model(id).nest_model(File.FullModel, "avatar")

    @classmethod
    def create(
        cls,
        name: str,
        creator_id: int,
        description: str | None,
    ) -> Self:
        entry: cls = super().create(
            name=name,
            description=description,
            owner_id=creator_id,
        )

        participant = Participant.add(
            user_id=creator_id,
            community_id=entry.id,
        )
        entry.participants.append(participant)
        db.session.add(participant)
        db.session.flush()
        return entry

    @classmethod
    def find_by_id(cls, entry_id: int) -> Self | None:
        return cls.find_first_not_deleted(id=entry_id)


class Participant(LinkedListNode, Identifiable):
    __tablename__ = "community_participant"

    id = Column(Integer, primary_key=True)

    user_id = Column(
        Integer,
        ForeignKey("communities_users.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )

    community_id = Column(
        Integer,
        ForeignKey("community.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    community = relationship("Community")

    roles = relationship("Role", secondary=ParticipantRole.__table__)

    prev_id = Column(
        Integer,
        ForeignKey(
            "community_participant.id", ondelete="SET NULL"
        ),  # TODO breaks the list?
        nullable=True,
    )
    prev = relationship(
        "Participant",
        remote_side=[id],
        foreign_keys=[prev_id],
    )

    next_id = Column(
        Integer,
        ForeignKey(
            "community_participant.id", ondelete="SET NULL"
        ),  # TODO breaks the list?
        nullable=True,
    )
    next = relationship(
        "Participant",
        remote_side=[id],
        foreign_keys=[next_id],
    )

    FullModel = PydanticModel.column_model(id, user_id, community_id).nest_model(
        Role.IndexModel, "roles", as_list=True
    )

    @classmethod
    def create(cls, community_id: int, user_id: int) -> Self:
        return super().create(
            community_id=community_id,
            user_id=user_id,
        )

    @classmethod
    def find_by_id(cls, participant_id: int) -> Self | None:
        return cls.find_first_by_kwargs(id=participant_id)

    @classmethod
    def find_by_ids(cls, community_id: int, user_id: int) -> Self | None:
        return cls.find_first_by_kwargs(community_id=community_id, user_id=user_id)

    @classmethod
    def get_communities_list(cls, user_id: int) -> list[Community]:
        root = aliased(cls)
        node = aliased(cls)

        cte = (
            select(root, literal(0).label("level"))
            .filter_by(user_id=user_id, prev_id=None)
            .cte("cte", recursive=True)
        )

        result = cte.union_all(
            select(node, cte.c.level + 1)
            .filter_by(user_id=user_id)
            .join(cte, node.prev_id == cte.c.id)
        )

        return db.get_all(
            Community.select_not_deleted()
            .join(result, Community.id == result.c.community_id)
            .order_by(cte.c.level)
        )

    @classmethod
    def search_by_username(
        cls,
        search: str | None,
        community_id: int,
        offset: int,
        limit: int,
    ) -> list[Participant]:
        stmt = (
            select(cls)
            .options(selectinload(cls.roles))
            .filter_by(community_id=community_id)
        )
        if search is not None:
            stmt = stmt.join(User, User.id == cls.user_id).filter(
                User.username.ilike(f"%{search}%")
            )
        return db.get_paginated(stmt, offset, limit)
