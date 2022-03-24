from __future__ import annotations

from typing import Union

from sqlalchemy import Column
from sqlalchemy.sql.sqltypes import Integer

from common import Base, sessionmaker


class BaseModuleSession(Base):
    __abstract__ = True
    not_found_text = "Session not found"

    user_id = Column(Integer, primary_key=True)  # TODO replace with relationship
    module_id = Column(Integer, primary_key=True)  # TODO replace with relationship

    @classmethod
    def find_by_ids(cls, session: sessionmaker, user_id: int, module_id: int) -> Union[BaseModuleSession, None]:
        return cls.find_first_by_kwargs(session, user_id=user_id, module_id=module_id)

    @classmethod
    def find_or_create(cls, session: sessionmaker, user_id: int, module_id: int) -> BaseModuleSession:
        entry = cls.find_by_ids(session, user_id, module_id)
        if entry is None:
            return cls.create(session, user_id=user_id, module_id=module_id)
        return entry
