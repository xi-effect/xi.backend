from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, select
from sqlalchemy.sql.sqltypes import Integer, Boolean, DateTime, Float

from componets import LambdaFieldDef, create_marshal_model, Marshalable, TypeEnum
from componets.checkers import first_or_none
from users import User
from main import Base, Session


class BaseModuleSession(Base):
    __abstract__ = True
    not_found_text = "Session not found"

    user_id = Column(Integer, primary_key=True)  # MB replace with relationship
    module_id = Column(Integer, primary_key=True)  # MB replace with relationship

    @classmethod
    def create(cls, session: Session, user_id: int, module_id: int) -> BaseModuleSession:
        raise NotImplementedError

    @classmethod
    def find_by_ids(cls, session: Session, user_id: int, module_id: int) -> Optional[BaseModuleSession]:
        return first_or_none(session.execute(select(cls).where(cls.user_id == user_id, cls.module_id == module_id)))

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
    def create(cls, session: Session, user_id: int, module_id: int) -> Optional[ModuleFilterSession]:
        if cls.find_by_ids(session, user_id, module_id) is not None:
            return None
        # parameter check freaks out for no reason \/ \/ \/
        new_entry = cls(user_id=user_id, module_id=module_id, last_changed=datetime.utcnow())  # noqa
        session.add(new_entry)
        return new_entry

    @classmethod
    def change_preference_by_user(cls, session: Session, user_id: int, operation: PreferenceOperation) -> None:
        filter_session: cls
        for filter_session in select(cls).filter_by(user_id=user_id).scalars().all():
            filter_session.change_preference(session, operation)

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


class StandardModuleSession(BaseModuleSession):
    __tablename__ = "standard_module_sessions"
    progress = Column(Integer, nullable=False, default=-1)
    theory_level = Column(Float, nullable=False, default=0.5)

    @classmethod
    def create(cls, session: Session, user_id: int, module_id: int) -> Optional[StandardModuleSession]:
        if cls.find_by_ids(session, user_id, module_id) is not None:
            return None
        new_entry = cls(user_id=user_id, module_id=module_id)
        session.add(new_entry)
        session.flush()
        return new_entry

    def get_theory_level(self, session: Session):
        return User.find_by_id(session, self.user_id).theory_level * 0.2 + self.theory_level * 0.8

    def delete(self, session: Session):
        session.delete(self)
        session.flush()


class TestModuleSession(BaseModuleSession):
    __tablename__ = "test-module-sessions"
    not_found_text = "Test session not found"

    pass  # keeps test instance (one to many) in keeper.py

    @classmethod
    def create(cls, session: Session, user_id: int, module_id: int) -> TestModuleSession:
        pass

    def get_task(self, session: Session, task_id: int) -> int:
        return 3  # temp

    def set_reply(self, session: Session, task_id: int, reply) -> None:
        pass

    def collect_results(self, session: Session) -> dict:
        pass  # delete the test_session!
