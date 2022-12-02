from __future__ import annotations

from typing import TypeVar, Callable

from flask_fullstack import Identifiable, PydanticModel, TypeEnum
from sqlalchemy import Column, ForeignKey, func, select, event
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import Integer, String, Enum
from sqlalchemy.engine import Engine

from common import Base, db
from communities.base import Community, Participant

LimitingQuantityRoles = 50


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(*args):
    cursor = args[0].cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


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
    community_id = Column(Integer, ForeignKey(Community.id, ondelete="CASCADE"))

    permissions = relationship("RolePermission", passive_deletes=True)

    BaseModel = PydanticModel.column_model(id)
    CreateModel = PydanticModel.column_model(name, color)
    IndexModel = BaseModel.combine_with(CreateModel)

    class FullModel(IndexModel):
        permissions: list[str]

        @classmethod
        def callback_convert(
            cls, callback: Callable, orm_object: Role, **context
        ) -> None:
            callback(
                permissions=[
                    permission.permission_type.to_string()
                    for permission in orm_object.permissions
                ]
            )

    def __repr__(self):
        return self.name

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

    role_id = Column(Integer, ForeignKey(Role.id, ondelete="CASCADE"), primary_key=True)
    permission_type = Column(Enum(PermissionTypes), primary_key=True)

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
    def delete_by_role(cls: type[p], role_id: int) -> None:
        smtp = db.delete(cls).where(cls.role_id == role_id)
        db.session.execute(smtp)


class ParticipantRole(Base):  # TODO pragma: no cover
    __tablename__ = "cs_participant_roles"

    participant_id = Column(
        Integer, ForeignKey(Participant.id, ondelete="CASCADE"), primary_key=True
    )
    role_id = Column(Integer, ForeignKey(Role.id, ondelete="CASCADE"), primary_key=True)
