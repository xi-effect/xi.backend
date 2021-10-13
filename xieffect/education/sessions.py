from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Sequence, select
from sqlalchemy.sql.sqltypes import Integer, Boolean, DateTime

from componets import Identifiable, LambdaFieldDef, create_marshal_model, Marshalable, TypeEnum
from componets.checkers import first_or_none
from main import Base, Session


class PreferenceOperation(TypeEnum):
    HIDE = 0
    SHOW = 1
    STAR = 2
    UNSTAR = 3
    PIN = 4
    UNPIN = 5


@create_marshal_model("mfs", "started", "starred", "pinned", use_defaults=True)
class ModuleFilterSession(Base, Marshalable):
    __tablename__ = "module-filter-sessions"
    not_found_text = "Session not found"

    user_id = Column(Integer, primary_key=True)  # MB replace with relationship
    module_id = Column(Integer, primary_key=True)  # MB replace with relationship

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
    def find_by_ids(cls, session: Session, user_id: int, module_id: int) -> Optional[ModuleFilterSession]:
        return first_or_none(session.execute(select(cls).where(cls.user_id == user_id, cls.module_id == module_id)))

    @classmethod
    def find_or_create(cls, session: Session, user_id: int, module_id: int) -> ModuleFilterSession:
        entry = cls.find_by_ids(session, user_id, module_id)
        if entry is None:
            return cls.create(session, user_id, module_id)
        return entry

    @classmethod
    def change_preference_by_user(cls, session: Session, user_id: int, operation: PreferenceOperation) -> None:
        filter_session: cls
        for filter_session in cls.query.filter_by(user_id=user_id).all():
            filter_session.change_preference(session, operation)

    def is_valuable(self) -> bool:
        return self.hidden or self.pinned or self.starred or self.started

    def visit_now(self) -> None:  # auto-commit
        self.last_visited = datetime.utcnow()
        self.note_change()

    def note_change(self) -> None:  # auto-commit
        self.last_changed = datetime.utcnow()

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
        if not (self.is_valuable()):
            session.delete(self)
            session.flush()
        else:
            self.note_change()


class BaseModuleSession(Base, Identifiable):
    __abstract__ = True
    not_found_text = "Session not found"

    id = Column(Integer, Sequence('ms_id_seq'), primary_key=True)
    user_id = Column(Integer, nullable=False)  # MB replace with relationship
    module_id = Column(Integer, nullable=False)  # MB replace with relationship

    @classmethod
    def create(cls, session: Session, user_id: int, module_id: int) -> BaseModuleSession:
        raise NotImplementedError

    @classmethod
    def find_by_id(cls, session: Session, entry_id: int) -> Optional[BaseModuleSession]:
        return first_or_none(session.execute(select(cls).where(cls.id == entry_id)))

    @classmethod
    def find_by_ids(cls, session: Session, user_id: int, module_id: int) -> Optional[BaseModuleSession]:
        return first_or_none(session.execute(select(cls).where(cls.user_id == user_id, cls.module_id == module_id)))

    @classmethod
    def find_or_create(cls, session: Session, user_id: int, module_id: int) -> BaseModuleSession:
        entry = cls.find_by_ids(session, user_id, module_id)
        if entry is None:
            return cls.create(session, user_id, module_id)
        return entry


class StandardModuleSession(BaseModuleSession):
    __tablename__ = "standard_module_sessions"
    progress = Column(Integer, nullable=False, default=0)

    @classmethod
    def create(cls, session: Session, user_id: int, module_id: int,
               progress: int = 0) -> Optional[StandardModuleSession]:
        if cls.find_by_ids(session, user_id, module_id) is not None:
            return None
        new_entry = cls(user_id=user_id, module_id=module_id, progress=progress)
        session.add(new_entry)
        return new_entry

    @classmethod
    def find_or_create_with_progress(cls, session: Session, user_id: int, module_id: int,
                                     progress: int) -> StandardModuleSession:
        entry: cls = cls.find_by_ids(session, user_id, module_id)
        if entry is None:
            entry = cls.create(session, user_id, module_id, progress)
        else:
            entry.progress = progress
        return entry

    @classmethod
    def set_progress_by_ids(cls, session: Session, user_id: int, module_id: int, progress: int) -> None:
        if progress != -1:  # module is not completed
            cls.find_or_create_with_progress(session, user_id, module_id, progress)
            return

        entry: cls = cls.find_by_ids(session, user_id, module_id)
        if entry is not None:
            session.delete(entry)

    # def set_progress(self):
    # pass

    def next_page_id(self) -> int:  # auto-commit
        self.point_id += 1
        return self.module_id  # temp
        # return self.execute_point()

    def execute_point(self, point_id: Optional[int] = None) -> int:  # auto-commit
        return self.point_id  # temp
        # if point_id is None:
        #     return Point.find_by_ids(self.course_id, self.module_id, self.point_id).execute()
        # else:
        #     return Point.find_by_ids(self.course_id, self.module_id, point_id).execute()


class TestModuleSession(BaseModuleSession):
    __tablename__ = "test-module-sessions"
    pass  # keeps test instance (one to many) in keeper.py

    @classmethod
    def create(cls, session: Session, user_id: int, module_id: int) -> TestModuleSession:
        pass

    def get_task(self, task_id: int) -> dict:
        pass

    def set_reply(self, session: Session, task_id: int, reply) -> None:
        pass

    def collect_results(self) -> dict:
        pass  # delete the session!
