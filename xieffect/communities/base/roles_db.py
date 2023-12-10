from __future__ import annotations

from collections.abc import Iterable
from typing import Self, ClassVar

from flask_fullstack import Identifiable, TypeEnum
from pydantic_marshals.sqlalchemy import MappedModel
from sqlalchemy import ForeignKey, select, distinct
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql.expression import and_
from sqlalchemy.sql.functions import count
from sqlalchemy.sql.sqltypes import String

from common import Base, db


class PermissionType(TypeEnum):
    MANAGE_COMMUNITY = -1
    MANAGE_INVITATIONS = 0
    MANAGE_ROLES = 1
    MANAGE_TASKS = 2
    MANAGE_NEWS = 3
    MANAGE_MESSAGES = 4
    MANAGE_PARTICIPANTS = 5


class Role(Base, Identifiable):
    __tablename__ = "cs_roles"
    max_count: ClassVar[int] = 50
    not_found_text = "Role not found"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(32))
    color: Mapped[str | None] = mapped_column(String(6))
    community_id: Mapped[int] = mapped_column(
        ForeignKey("community.id", ondelete="CASCADE")
    )

    permissions_r: Mapped[list[RolePermission]] = relationship(passive_deletes=True)

    @property
    def permissions(self) -> list[str]:
        return [
            permission.permission_type.to_string() for permission in self.permissions_r
        ]

    CreateModel = MappedModel.create(columns=[name, color])
    IndexModel = CreateModel.extend(columns=[id])
    FullModel = IndexModel.extend(properties=[permissions])

    @classmethod
    def create(
        cls,
        name: str,
        color: str | None,
        community_id: int,
    ) -> Self:
        return super().create(
            name=name,
            color=color,
            community_id=community_id,
        )

    @classmethod
    def find_by_id(cls, entry_id: int) -> Self | None:
        return cls.find_first_by_kwargs(id=entry_id)

    @classmethod
    def find_by_community(cls, community_id: int) -> list[Self]:
        return cls.find_all_by_kwargs(community_id=community_id)

    @classmethod
    def get_count_by_community(cls, community_id: int) -> int:
        return db.get_first(select(count(cls.id)).filter_by(community_id=community_id))


class RolePermission(Base):
    __tablename__ = "cs_role_permissions"

    role_id: Mapped[int] = mapped_column(
        ForeignKey(Role.id, ondelete="CASCADE"),
        primary_key=True,
    )
    permission_type: Mapped[PermissionType] = mapped_column(primary_key=True)

    @classmethod
    def create_bulk(cls, role_id: int, permissions: list[PermissionType]) -> None:
        db.session.add_all(
            cls(role_id=role_id, permission_type=permission)
            for permission in permissions
        )
        db.session.flush()

    @classmethod
    def delete_by_ids(cls, role_id: int, permissions_type: set[PermissionType]) -> None:
        db.session.execute(
            db.delete(cls).filter(
                cls.role_id == role_id, cls.permission_type.in_(permissions_type)
            )
        )

    @classmethod
    def get_all_by_role(cls, role_id: int) -> list[Self]:
        return db.get_all(select(cls).filter_by(role_id=role_id))


class ParticipantRole(Base):
    __tablename__ = "cs_participant_roles"

    participant_id: Mapped[int] = mapped_column(
        ForeignKey("community_participant.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role_id: Mapped[int] = mapped_column(
        ForeignKey(Role.id, ondelete="CASCADE"),
        primary_key=True,
    )

    @classmethod
    def deny_permission(cls, participant_id: int, permission: PermissionType) -> bool:
        return (
            db.get_first(
                select(distinct(RolePermission.permission_type))
                .join(Role, Role.id == RolePermission.role_id)
                .join(
                    cls,
                    and_(cls.role_id == Role.id, cls.participant_id == participant_id),
                )
                .filter(RolePermission.permission_type == permission)
            )
            is None
        )

    @classmethod
    def get_role_ids(cls, participant_id: int) -> list[int]:
        return db.get_all(select(cls.role_id).filter_by(participant_id=participant_id))

    @classmethod
    def create_bulk(cls, participant_id: int, role_ids: Iterable[int]) -> None:
        db.session.add_all(
            cls(participant_id=participant_id, role_id=role_id) for role_id in role_ids
        )
        db.session.flush()

    @classmethod
    def delete_by_ids(cls, participant_id: int, role_ids: set[int]) -> None:
        db.session.execute(
            db.delete(cls).filter(
                cls.participant_id == participant_id, cls.role_id.in_(role_ids)
            )
        )
