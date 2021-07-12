from typing import Optional, Dict, List
from datetime import datetime

from flask_sqlalchemy import BaseQuery

from base.basic import Identifiable
from main import db


class ModuleFilterSession(db.Model):
    not_found_text = "Session not found"

    user_id = db.Column(db.Integer, primary_key=True)  # MB replace with relationship
    module_id = db.Column(db.Integer, primary_key=True)  # MB replace with relationship

    started = db.Column(db.Boolean, nullable=False, default=False)
    starred = db.Column(db.Boolean, nullable=False, default=False)
    pinned = db.Column(db.Boolean, nullable=False, default=False)
    hidden = db.Column(db.Boolean, nullable=False, default=False)

    last_visited = db.Column(db.DateTime, nullable=True)  # None for not visited
    last_changed = db.Column(db.DateTime, nullable=True)

    @classmethod
    def create(cls, user_id: int, module_id: int):
        if cls.find_by_ids(user_id, module_id) is not None:
            return None
        new_entry = cls(user_id=user_id, module_id=module_id, last_changed=datetime.utcnow())
        db.session.add(new_entry)
        db.session.commit()
        return new_entry

    @classmethod
    def find_by_ids(cls, user_id: int, module_id: int):
        return cls.query.filter_by(user_id=user_id, module_id=module_id).first()

    @classmethod
    def find_or_create(cls, user_id: int, module_id: int):  # check if ever used
        entry = cls.find_by_ids(user_id, module_id)
        if entry is None:
            return cls.create(user_id, module_id)
        return entry

    @classmethod
    def find_json(cls, user_id: int, module_id: int) -> Dict[str, bool]:
        entry: cls = cls.find_by_ids(user_id, module_id)
        if entry is None:
            return dict.fromkeys(("hidden", "pinned", "starred", "started"), False)
        return entry.to_json()

    @classmethod
    def find_visit_date(cls, user_id: int, module_id: int) -> float:
        entry: cls = cls.find_by_ids(user_id, module_id)
        if entry is None:
            return -1
        return entry.get_visit_date()

    @classmethod
    def filter_ids_by_user(cls, user_id: int, offset: int = None,
                           limit: int = None, **params) -> List[int]:
        query: BaseQuery = cls.query.filter_by(user_id=user_id, **params)
        query = query.order_by(cls.last_changed)

        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)

        return [x.course_id for x in query.all()]

    @classmethod
    def change_preference_by_user(cls, user_id: int, operation: str, **params) -> None:
        filter_session: cls
        for filter_session in cls.query.filter_by(user_id=user_id, **params).all():
            filter_session.change_preference(operation)

    def is_valuable(self) -> bool:
        return self.hidden or self.pinned or self.starred or self.started

    def to_json(self) -> Dict[str, bool]:
        return {
            "hidden": self.hidden, "pinned": self.pinned,
            "starred": self.starred, "started": self.started
        }

    def get_visit_date(self) -> float:
        return self.last_visited.timestamp() if self.last_visited is not None else -1

    def visit_now(self) -> None:
        self.last_visited = datetime.utcnow()
        self.note_change()

    def note_change(self) -> None:
        self.last_changed = datetime.utcnow()
        db.session.commit()

    def change_preference(self, operation: str) -> None:
        if operation == "hide":
            self.hidden = True
        elif operation == "show":
            self.hidden = False
        elif operation == "star":
            self.starred = True
        elif operation == "unstar":
            self.starred = False
        elif operation == "pin":
            self.pinned = True
        elif operation == "unpin":
            self.pinned = False
        if not (self.is_valuable()):
            db.session.delete(self)
        else:
            self.note_change()
        db.session.commit()


class BaseModuleSession(db.Model, Identifiable):
    __abstract__ = True
    not_found_text = "Session not found"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)  # MB replace with relationship
    module_id = db.Column(db.Integer, nullable=False)  # MB replace with relationship

    @classmethod
    def create(cls, user_id: int, module_id: int):
        raise NotImplementedError

    @classmethod
    def find_by_id(cls, entry_id: int):
        return cls.query.filter_by(id=entry_id).first()

    @classmethod
    def find_by_ids(cls, user_id: int, module_id: int):
        return cls.query.filter_by(user_id=user_id, module_id=module_id).first()

    @classmethod
    def find_or_create(cls, user_id: int, module_id: int):
        entry = cls.find_by_ids(user_id, module_id)
        if entry is None:
            return cls.create(user_id, module_id)
        return entry


class StandardModuleSession(BaseModuleSession):
    __tablename__ = "standard_module_sessions"
    progress = db.Column(db.Integer, nullable=False, default=0)

    @classmethod
    def create(cls, user_id: int, module_id: int, progress: int = 0):
        if cls.find_by_ids(user_id, module_id) is not None:
            return None
        new_entry = cls(user_id=user_id, module_id=module_id, progress=progress)
        db.session.add(new_entry)
        db.session.commit()
        return new_entry

    @classmethod
    def find_or_create_with_progress(cls, user_id: int, module_id: int, progress: int):
        entry: cls = cls.find_by_ids(user_id, module_id)
        if entry is None:
            entry = cls.create(user_id, module_id, progress)
        else:
            entry.progress = progress
            db.session.commit()
        return entry

    @classmethod
    def set_progress_by_ids(cls, user_id: int, module_id: int, progress: int):
        if progress != -1:  # module is not completed
            cls.find_or_create_with_progress(user_id, module_id, progress)
            return

        entry: cls = cls.find_by_ids(user_id, module_id)
        if entry is not None:
            db.session.delete(entry)
            db.session.commit()

    # def set_progress(self):
        # pass

    def next_page_id(self) -> int:
        self.point_id += 1
        return self.module_id  # temp
        # return self.execute_point()

    def execute_point(self, point_id: Optional[int] = None) -> int:
        return self.point_id  # temp
        # if point_id is None:
        #     return Point.find_by_ids(self.course_id, self.module_id, self.point_id).execute()
        # else:
        #     return Point.find_by_ids(self.course_id, self.module_id, point_id).execute()


class TestModuleSession(BaseModuleSession):
    pass  # keeps test instance (one to many) in keeper.py

    @classmethod
    def create(cls, user_id: int, module_id: int):
        pass

    def get_task(self, task_id: int) -> dict:
        pass

    def set_reply(self, task_id: int, reply):
        pass

    def collect_results(self) -> dict:
        pass  # delete the session!
