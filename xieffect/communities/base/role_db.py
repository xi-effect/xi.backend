from flask_fullstack import Identifiable, PydanticModel
from flask_fullstack import TypeEnum
from sqlalchemy import Column, ForeignKey, select
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import Integer, String, Enum
from typing import TypeVar

from common import Base
from communities.base import Community, Participant


class PermissionTypes(TypeEnum):
    pass


t = TypeVar("t", bound="Role")


class Role(Base, Identifiable):
    __tablename__ = "cs_roles"

    not_found_text = "role not found"

    id = Column(Integer, primary_key=True)
    name = Column(String(32), nullable=False)
    color = Column(String(6), nullable=True)
    community_id = Column(Integer, ForeignKey(Community.id, ondelete="CASCADE"), primary_key=True)

    BaseModel = PydanticModel.column_model(id)
    CreateModel = PydanticModel.column_model(name, color)
    IndexModel = BaseModel.combine_with(CreateModel)

    @classmethod
    def get_all(cls: type[t]) -> list[t]:
        return cls.query.all()


class RolePermission(Base):
    __tablename__ = "cs_role_permissions"

    role_id = Column(Integer, ForeignKey(Role.id), primary_key=True)
    permission_type = Column(Enum(PermissionTypes), primary_key=True)

    role = relationship("Role", cascade="all, delete, delete-orphan", single_parent=True)


class ParticipantRole(Base):
    __tablename__ = "cs_participant_roles"

    participant_id = Column(Integer, ForeignKey(Participant.id), primary_key=True)
    role_id = Column(Integer, ForeignKey(Role.id), primary_key=True)

    participants = relationship("Participant", cascade="all, delete, delete-orphan", single_parent=True)
    role = relationship("Role", cascade="all, delete, delete-orphan", single_parent=True)
