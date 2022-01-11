from __future__ import annotations

from datetime import datetime
from typing import Union

from sqlalchemy import Column, select, ForeignKeyConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import Integer, Boolean, DateTime, Float, JSON

from componets import LambdaFieldDef, create_marshal_model, Marshalable, TypeEnum
from main import Base, Session
from users import User


class BaseModuleSession(Base):
    __abstract__ = True
    not_found_text = "Session not found"

    user_id = Column(Integer, primary_key=True)  # MB replace with relationship
    module_id = Column(Integer, primary_key=True)  # MB replace with relationship

    @classmethod
    def create(cls, session: Session, user_id: int, module_id: int) -> BaseModuleSession:
        raise NotImplementedError

    @classmethod
    def find_by_ids(cls, session: Session, user_id: int, module_id: int) -> Union[BaseModuleSession, None]:
        return session.execute(select(cls).filter(cls.user_id == user_id, cls.module_id == module_id)).scalars().first()

    @classmethod
    def find_or_create(cls, session: Session, user_id: int, module_id: int) -> BaseModuleSession:
        entry = cls.find_by_ids(session, user_id, module_id)
        if entry is None:
            return cls.create(session, user_id, module_id)
        return entry


class PreferenceOperation(TypeEnum):
    HIDE = 0
    SHOW = 1
    STAR = 2
    UNSTAR = 3
    PIN = 4
    UNPIN = 5


@create_marshal_model("mfs-full", "started", "starred", "pinned", use_defaults=True)
class ModuleFilterSession(BaseModuleSession, Marshalable):
    __tablename__ = "module-filter-sessions"
    not_found_text = "Session not found"

    started = Column(Boolean, nullable=False, default=False)
    starred = Column(Boolean, nullable=False, default=False)
    pinned = Column(Boolean, nullable=False, default=False)
    hidden = Column(Boolean, nullable=False, default=False)

    last_visited = Column(DateTime, nullable=True)  # None for not visited
    last_changed = Column(DateTime, nullable=True)

    visited: LambdaFieldDef = \
        LambdaFieldDef("mfs", datetime, lambda mfs: mfs.last_visited if mfs.started else datetime.min)

    @classmethod
    def create(cls, session: Session, user_id: int, module_id: int) -> Union[ModuleFilterSession, None]:
        if cls.find_by_ids(session, user_id, module_id) is not None:
            return None
        # parameter check freaks out for no reason \/ \/ \/
        new_entry = cls(user_id=user_id, module_id=module_id, last_changed=datetime.utcnow())  # noqa
        session.add(new_entry)
        session.flush()
        return new_entry

    def note_change(self) -> None:  # auto-commit
        self.last_changed = datetime.utcnow()

    def visit_now(self) -> None:  # auto-commit
        self.last_visited = datetime.utcnow()
        self.note_change()

    def change_preference(self, session: Session, operation: PreferenceOperation) -> None:
        if operation == PreferenceOperation.HIDE:
            self.hidden = True
        elif operation == PreferenceOperation.SHOW:
            self.hidden = False
        elif operation == PreferenceOperation.STAR:
            self.starred = True
        elif operation == PreferenceOperation.UNSTAR:
            self.starred = False
        elif operation == PreferenceOperation.PIN:
            self.pinned = True
        elif operation == PreferenceOperation.UNPIN:
            self.pinned = False
        if not any((self.hidden, self.pinned, self.starred, self.started)):
            session.delete(self)
            session.flush()
        else:
            self.note_change()


class ModuleProgressSession(BaseModuleSession):
    __tablename__ = "standard_module_sessions"
    progress = Column(Integer, nullable=True)
    theory_level = Column(Float, nullable=True)  # temp disabled for theory blocks

    @classmethod
    def create(cls, session: Session, user_id: int, module_id: int) -> Union[ModuleProgressSession, None]:
        if cls.find_by_ids(session, user_id, module_id) is not None:
            return None
        new_entry = cls(user_id=user_id, module_id=module_id)
        session.add(new_entry)
        session.flush()
        return new_entry

    def get_theory_level(self, session: Session) -> Union[float, None]:
        if self.theory_level is None:
            return None
        return User.find_by_id(session, self.user_id).theory_level * 0.2 + self.theory_level * 0.8

    def delete(self, session: Session):
        session.delete(self)
        session.flush()


class TestModuleSession(BaseModuleSession):
    __tablename__ = "test_module_sessions"
    not_found_text = "Test session not found"
    points = relationship("TestPointSession", cascade="all, delete")

    @classmethod
    def create(cls, session: Session, user_id: int, module_id: int) -> TestModuleSession:
        new_entry = cls(user_id=user_id, module_id=module_id)
        session.add(new_entry)
        session.flush()
        return new_entry

    def create_point_session(self, session: Session, point_id: int, module) -> TestPointSession:
        page_id = module.execute_point(point_id)
        new_entry = TestPointSession(page_id=page_id, point_id=point_id)
        self.points.append(new_entry)
        session.flush()
        return new_entry

    def find_point_session(self, session: Session, point_id: int) -> Union[TestPointSession, None]:
        return TestPointSession.find_by_ids(session, user_id=self.user_id, module_id=self.module_id, point_id=point_id)

    def collect_all(self, session: Session) -> list[TestPointSession]:
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
    def find_by_ids(cls, session: Session, user_id: int, module_id: int, point_id) -> Union[TestModuleSession, None]:
        return session.execute(select(cls).filter(cls.user_id == user_id, cls.module_id == module_id,
                                                  cls.point_id == point_id)).scalars().first()
