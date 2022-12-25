from __future__ import annotations

from collections.abc import Callable

from flask_fullstack import Identifiable, PydanticModel, TypeEnum
from sqlalchemy import Column, ForeignKey, select, distinct
from sqlalchemy.orm import relationship
from sqlalchemy.sql.functions import count
from sqlalchemy.sql.sqltypes import Integer, String, Enum

from .meta_db import Base, db, Community, Participant

LIMITING_QUANTITY_ROLES: int = 50


class PermissionType(TypeEnum):
    MANAGE_INVITATIONS = 0
    MANAGE_ROLES = 1
    MANAGE_TASKS = 2
    MANAGE_NEWS = 3
    MANAGE_MESSAGES = 4


class Role(Base, Identifiable):
    __tablename__ = "cs_roles"
    not_found_text = "Role not found"

    id = Column(Integer, primary_key=True)
    name = Column(String(32), nullable=False)
    color = Column(String(6), nullable=True)
    community_id = Column(
        Integer, ForeignKey(Community.id, ondelete="CASCADE"), nullable=False
    )

    permissions = relationship("RolePermission", passive_deletes=True)

    CreateModel = PydanticModel.column_model(name, color)
    IndexModel = CreateModel.column_model(id)

    class FullModel(IndexModel):
        permissions: list[str]

        @classmethod
        def callback_convert(cls, callback: Callable, orm_object: Role, **_) -> None:
            callback(
                permissions=[
                    permission.permission_type.to_string()
                    for permission in orm_object.permissions
                ]
            )

    @classmethod
    def create(
            cls,
            name: str,
            color: str | None,
            community_id: int,
    ) -> Role:
        return super().create(
            name=name,
            color=color,
            community_id=community_id,
        )

    @classmethod
    def find_by_id(cls, role_id: int) -> Role | None:
        return db.session.get_first(select(cls).filter_by(id=role_id))

    @classmethod
    def find_by_community(cls, community_id: int) -> list[Role]:
        return db.session.get_all(select(cls).filter_by(community_id=community_id))

    @classmethod
    def get_count_by_community(cls, community_id: int) -> int:
        return db.session.get_first(
            select(count(cls.id)).filter_by(community_id=community_id)
        )


class RolePermission(Base):
    __tablename__ = "cs_role_permissions"

    role_id = Column(
        Integer,
        ForeignKey(Role.id, ondelete="CASCADE"),
        primary_key=True,
    )
    permission_type = Column(Enum(PermissionType), primary_key=True)

    @classmethod
    def create(
            cls,
            role_id: int,
            permission_type: PermissionType,
    ) -> RolePermission:
        return super().create(
            role_id=role_id,
            permission_type=permission_type,
        )

    @classmethod
    def delete_by_role(cls, role_id: int, permission_type: str) -> None:
        db.session.execute(
            db.delete(cls).where(
                cls.role_id == role_id, cls.permission_type == permission_type
            )
        )

    @classmethod
    def get_all_by_role(cls, role_id: int) -> list[RolePermission]:
        return db.session.get_all(select(cls).filter_by(role_id=role_id))


class ParticipantRole(Base):  # TODO pragma: no cover
    __tablename__ = "cs_participant_roles"

    participant_id = Column(
        Integer, ForeignKey(Participant.id, ondelete="CASCADE"), primary_key=True
    )
    role_id = Column(Integer, ForeignKey(Role.id, ondelete="CASCADE"), primary_key=True)

    # @classmethod
    # def get_permissions_by_participant(cls, participant_id: int) -> list[PermissionType]:
    #     return db.session.get_all(
    #         select(Role).join_from(Role, cls).filter_by(participant_id=participant_id)
    #     )

    @classmethod
    def get_permissions_by_participant(cls, participant_id: int):
        return db.session.get_all(
            select(distinct(RolePermission.permission_type))
            .join(cls, cls.role_id == Role.id)
            .filter_by(participant_id=participant_id)
            .join(Role, Role.id == RolePermission.role_id)
        )
