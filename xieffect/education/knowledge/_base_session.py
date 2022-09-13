from __future__ import annotations

from sqlalchemy import Column
from sqlalchemy.sql.sqltypes import Integer

from common import Base, PydanticModel


class BaseModuleSession(Base):
    __abstract__ = True
    not_found_text = "Session not found"

    user_id = Column(Integer, primary_key=True)
    module_id = Column(Integer, primary_key=True)

    BaseModel = PydanticModel.column_model(user_id=user_id, module_id=module_id)

    @classmethod
    def find_by_ids(cls, user_id: int, module_id: int) -> BaseModuleSession | None:
        return cls.find_first_by_kwargs(user_id=user_id, module_id=module_id)

    @classmethod
    def find_or_create(cls, user_id: int, module_id: int) -> BaseModuleSession:
        entry = cls.find_by_ids(user_id, module_id)
        if entry is None:
            return cls.create(user_id=user_id, module_id=module_id)
        return entry
