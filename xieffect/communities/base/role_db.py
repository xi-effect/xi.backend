from __future__ import annotations

from typing import TypeVar

from flask_fullstack import Identifiable, PydanticModel, TypeEnum
from sqlalchemy import Column, ForeignKey, func, select
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import Integer, String, Enum

from common import Base, db
from communities.base import Community, Participant

LimitingQuantityRoles: int = 50


class PermissionTypes(TypeEnum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"


r = TypeVar("r", bound="Role")
p = TypeVar("p", bound="RolePermission")


class Role(Base, Identifiable):
    __tablename__ = "cs_roles"

    not_found_text = "role not found"

    id = Column(Integer, primary_key=True)
    name = Column(String(32), nullable=False)
    color = Column(String(6), nullable=True)
    community_id = Column(
        Integer, ForeignKey(Community.id, ondelete="CASCADE")
    )

    BaseModel = PydanticModel.column_model(id)
    CreateModel = PydanticModel.column_model(name, color)
    IndexModel = BaseModel.column_model(community_id).combine_with(CreateModel)

    @classmethod
    def create(
        cls: type[r],
        name: str,
        color: str | None,
        community_id: int,
    ) -> type[r]:
        return super().create(
            name=name,
            color=color,
            community_id=community_id,
        )

    @classmethod
    def get_all(cls: type[r]) -> list[r]:
        return db.session.execute(select(cls)).all()

    @classmethod
    def get_count(cls: type[r], community_id: int) -> int:
        return db.session.execute(
            select(func.count())
            .select_from(cls)
            .where(cls.community_id == community_id)
        ).scalar()


class RolePermission(Base):
    __tablename__ = "cs_role_permissions"

    role_id = Column(Integer, ForeignKey(Role.id), primary_key=True)
    permission_type = Column(Enum(PermissionTypes), primary_key=True)

    role = relationship(
        "Role", cascade="all, delete, delete-orphan", single_parent=True
    )

    @classmethod
    def create(
        cls: type[p],
        role_id,
        permission_type,
    ) -> type[p]:
        return super().create(
            role_id=role_id,
            permission_type=permission_type,
        )


class ParticipantRole(Base):
    __tablename__ = "cs_participant_roles"

    participant_id = Column(Integer, ForeignKey(Participant.id), primary_key=True)
    role_id = Column(Integer, ForeignKey(Role.id), primary_key=True)

    participants = relationship(
        "Participant", cascade="all, delete, delete-orphan", single_parent=True
    )
    role = relationship(
        "Role", cascade="all, delete, delete-orphan", single_parent=True
    )
