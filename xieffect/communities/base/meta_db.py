from __future__ import annotations

from collections.abc import Callable
from typing import Self

from flask_fullstack import Identifiable, PydanticModel
from pydantic_marshals.sqlalchemy import MappedModel
from sqlalchemy import Column, ForeignKey, select, literal, distinct, and_
from sqlalchemy.orm import aliased, relationship, selectinload, Mapped, mapped_column
from sqlalchemy.sql.sqltypes import Integer, String, Text

from common import db
from common.abstract import SoftDeletable, LinkedListNode
from communities.base.roles_db import (
    ParticipantRole,
    Role,
    PermissionType,
    RolePermission,
)
from vault.files_db import File


class Community(SoftDeletable, Identifiable):
    __tablename__ = "community"
    not_found_text = "Community not found"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)

    avatar_id: Mapped[int | None] = mapped_column(
        ForeignKey("files.id", ondelete="SET NULL"),
    )
    avatar: Mapped[File | None] = relationship(foreign_keys=[avatar_id])

    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    # TODO ondelete is temporary

    CreateModel = MappedModel.create(columns=[name, description])
    UpdateModel = CreateModel.extend(columns=[avatar_id]).as_patch()
    IndexModel = CreateModel.extend(
        columns=[id],
        relationships=[(avatar, File.FullModel, True)],
    )

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
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    community_id = Column(
        Integer,
        ForeignKey("community.id", ondelete="CASCADE"),
        nullable=False,
    )
    community = relationship("Community", passive_deletes=True)

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
    _IndexModel = (
        PydanticModel.column_model(id)
        .nest_model(Community.IndexModel, "community")
        .nest_model(Role.IndexModel, "roles", as_list=True)
    )

    class IndexModel(_IndexModel):
        permissions: list[str]

        @classmethod
        def callback_convert(
            cls, callback: Callable, orm_object: Participant, **_
        ) -> None:
            callback(
                permissions=[
                    permission.to_string() for permission in orm_object.permissions
                ]
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
        from users.users_db import User  # TODO fix

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

    @property
    def permissions(self) -> list[PermissionType]:
        if self.community.owner_id == self.user_id:
            return list(PermissionType)
        return db.get_all(  # TODO pragma: no coverage
            select(distinct(RolePermission.permission_type))
            .join(Role, Role.id == RolePermission.role_id)
            .join(
                ParticipantRole,
                and_(
                    ParticipantRole.role_id == Role.id,
                    ParticipantRole.participant_id == self.id,
                ),
            )
        )
