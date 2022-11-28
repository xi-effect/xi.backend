from __future__ import annotations

from typing import TypeVar

from flask_fullstack import Identifiable, PydanticModel, TypeEnum
from sqlalchemy import Column, ForeignKey, func, select
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import Integer, String, Enum

from common import Base, db
from communities.base import Community, Participant

LimitingQuantityRoles = 50


class PermissionTypes(TypeEnum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"

    def __str__(self):
        return self.value


r = TypeVar("r", bound="Role")
p = TypeVar("p", bound="RolePermission")


class Role(Base, Identifiable):
    __tablename__ = "cs_roles"

    not_found_text = "role not found"

    id = Column(Integer, primary_key=True)
    name = Column(String(32), nullable=False)
    color = Column(String(6), nullable=True)
    community_id = Column(Integer, ForeignKey(Community.id, ondelete="CASCADE"))

    BaseModel = PydanticModel.column_model(id)
    CreateModel = PydanticModel.column_model(name, color)
    IndexModel = BaseModel.combine_with(CreateModel)

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
    def find_by_id(cls: type[r], role_id: int) -> r | None:
        return db.session.get_first(select(cls).filter_by(id=role_id))

    @classmethod
    def find_by_community(cls: type[r], community_id: int) -> list[r]:
        stmt = select(cls).filter_by(community_id=community_id)
        return db.session.get_all(stmt)

    @classmethod
    def get_count_by_community(cls: type[r], community_id: int) -> int:
        return db.session.execute(
            select(func.count()).select_from(cls).filter_by(community_id=community_id)
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

    @classmethod
    def find_by_role(cls: type[p], role_id: int):
        return db.session.get_all(select(cls).filter_by(role_id=role_id))

    @classmethod
    def delete_by_role(cls: type[p], role_id: int) -> None:
        smtp = db.delete(cls).where(cls.role_id == role_id)
        db.session.execute(smtp)


class ParticipantRole(Base):  # TODO pragma: no cover
    __tablename__ = "cs_participant_roles"

    participant_id = Column(Integer, ForeignKey(Participant.id), primary_key=True)
    role_id = Column(Integer, ForeignKey(Role.id), primary_key=True)

    participants = relationship(
        "Participant", cascade="all, delete, delete-orphan", single_parent=True
    )
    role = relationship(
        "Role", cascade="all, delete, delete-orphan", single_parent=True
    )
