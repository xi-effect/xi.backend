from __future__ import annotations

from typing import Union

from sqlalchemy import Column, select, ForeignKeyConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import Integer, Float, JSON

from common import create_marshal_model, Marshalable, User, Base, sessionmaker
from ._base_session import BaseModuleSession


class ModuleProgressSession(BaseModuleSession):
    __tablename__ = "standard_module_sessions"
    progress = Column(Integer, nullable=True)
    theory_level = Column(Float, nullable=True)  # temp disabled for theory blocks

    @classmethod
    def create(cls, session: sessionmaker, user_id: int, module_id: int) -> Union[ModuleProgressSession, None]:
        if cls.find_by_ids(session, user_id, module_id) is not None:
            return None
        new_entry = cls(user_id=user_id, module_id=module_id)
        session.add(new_entry)
        session.flush()
        return new_entry

    def get_theory_level(self, session: sessionmaker) -> Union[float, None]:
        if self.theory_level is None:
            return None
        return User.find_by_id(session, self.user_id).theory_level * 0.2 + self.theory_level * 0.8

    def delete(self, session: sessionmaker):
        session.delete(self)
        session.flush()


class TestModuleSession(BaseModuleSession):
    __tablename__ = "test_module_sessions"
    not_found_text = "Test session not found"
    points = relationship("TestPointSession", cascade="all, delete")

    @classmethod
    def create(cls, session: sessionmaker, user_id: int, module_id: int) -> TestModuleSession:
        new_entry = cls(user_id=user_id, module_id=module_id)
        session.add(new_entry)
        session.flush()
        return new_entry

    def create_point_session(self, session: sessionmaker, point_id: int, module) -> TestPointSession:
        page_id = module.execute_point(point_id)
        new_entry = TestPointSession(page_id=page_id, point_id=point_id)
        self.points.append(new_entry)
        session.flush()
        return new_entry

    def find_point_session(self, session: sessionmaker, point_id: int) -> Union[TestPointSession, None]:
        return TestPointSession.find_by_ids(session, user_id=self.user_id, module_id=self.module_id, point_id=point_id)

    def collect_all(self, session: sessionmaker) -> list[TestPointSession]:
        session.delete(self)
        return self.points


@create_marshal_model("TestPointSession", "point_id", "page_id", "right_answers", "total_answers", "answers")
class TestPointSession(Base, Marshalable):
    __tablename__ = "test-point-sessions"
    __table_args__ = (
        ForeignKeyConstraint(("module_id", "user_id"),
                             ("test_module_sessions.module_id", "test_module_sessions.user_id")),)
    module_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, primary_key=True)
    point_id = Column(Integer, primary_key=True)
    page_id = Column(Integer, nullable=False)
    right_answers = Column(Integer, nullable=True)
    total_answers = Column(Integer, nullable=True)
    answers = Column(JSON, nullable=True)

    @classmethod
    def find_by_ids(cls, session: sessionmaker, user_id: int, module_id: int, point_id) -> Union[TestModuleSession, None]:
        return session.execute(select(cls).filter(cls.user_id == user_id, cls.module_id == module_id,
                                                  cls.point_id == point_id)).scalars().first()
