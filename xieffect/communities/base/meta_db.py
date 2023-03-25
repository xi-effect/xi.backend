from __future__ import annotations

from typing import Self

from flask_fullstack import Identifiable, TypeEnum, PydanticModel
from sqlalchemy import Column, ForeignKey, select, Boolean, literal
from sqlalchemy.orm import relationship, aliased
from sqlalchemy.sql.sqltypes import Integer, String, Text, Enum

from common import Base, db
from common.abstract import LinkedListNode
from vault.files_db import File


class Community(Base, Identifiable):
    __tablename__ = "community"
    not_found_text = "Community not found"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    invite_count = Column(Integer, nullable=False, default=0)
    deleted = Column(Boolean, nullable=False, default=False)

    avatar_id = Column(
        Integer,
        ForeignKey("files.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
    )
    avatar = relationship("File", foreign_keys=[avatar_id])

    participants = relationship(
        "Participant",
        back_populates="community",
        cascade="all, delete",
        passive_deletes=True,
    )

    CreateModel = PydanticModel.column_model(name, description)
    IndexModel = CreateModel.column_model(id).nest_model(File.FullModel, "avatar")

    @classmethod
    def create(
        cls,
        name: str,
        creator_id: int,
        description: str | None,
    ) -> Self:
        entry: cls = super().create(name=name, description=description)
        participant = Participant.add(
            user_id=creator_id,
            community_id=entry.id,
            role=ParticipantRole.OWNER,
        )
        entry.participants.append(participant)
        db.session.add(participant)
        db.session.flush()
        return entry

    @classmethod
    def find_by_id(cls, entry_id: int) -> Self | None:
        return cls.find_first_by_kwargs(id=entry_id, deleted=False)


class ParticipantRole(TypeEnum):
    BASE = 0
    OWNER = 4


class Participant(LinkedListNode, Identifiable):
    __tablename__ = "community_participant"

    id = Column(Integer, primary_key=True)
    role = Column(Enum(ParticipantRole), nullable=False)

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
    community = relationship("Community", back_populates="participants")

    prev_id = Column(
        Integer,
        ForeignKey("community_participant.id", ondelete="SET NULL"),
        nullable=True,
    )
    prev = relationship(
        "Participant",
        remote_side=[id],
        foreign_keys=[prev_id],
    )

    next_id = Column(
        Integer,
        ForeignKey("community_participant.id", ondelete="SET NULL"),
        nullable=True,
    )
    next = relationship(
        "Participant",
        remote_side=[id],
        foreign_keys=[next_id],
    )

    @classmethod
    def create(cls, community_id: int, user_id: int, role: ParticipantRole) -> Self:
        return super().create(
            community_id=community_id,
            user_id=user_id,
            role=role,
        )

    @classmethod
    def find_by_ids(cls, community_id: int, user_id: int) -> Self | None:
        return cls.find_first_by_kwargs(community_id=community_id, user_id=user_id)

    @classmethod
    def get_communities_list(cls, user_id: int) -> list[Self]:
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
            select(Community)
            .filter_by(deleted=False)
            .join(result, Community.id == result.c.community_id)
            .order_by(cte.c.level)
        )
