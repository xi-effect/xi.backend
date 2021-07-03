from typing import Optional, Dict, List
from datetime import datetime

from flask_sqlalchemy import BaseQuery

from database.base.basic import Identifiable
from main import db


class ModuleSession(db.Model):
    __tablename__ = "module_sessions"

    user_id = db.Column(db.Integer, primary_key=True)  # MB replace with relationship
    course_id = db.Column(db.Integer, primary_key=True)  # MB replace with relationship
    module_id = db.Column(db.Integer, primary_key=True)
    points = db.Column(db.Integer, nullable=False, default=0)

    @classmethod
    def create(cls, user_id: int, course_id: int, module_id: int):
        if cls.find_by_id(user_id, course_id, module_id) is not None:
            return None
        new_entry = cls(user_id, course_id, module_id)
        db.session.add(new_entry)
        db.session.commit()
        return new_entry

    @classmethod
    def find_by_id(cls, user_id: int, course_id: int, module_id: int):
        return cls.query.filter_by(user_id=user_id, course_id=course_id, module_id=module_id).first()


class CourseSession(db.Model):
    __tablename__ = "course_sessions"

    user_id = db.Column(db.Integer, primary_key=True)  # MB replace with relationship
    course_id = db.Column(db.Integer, primary_key=True)  # MB replace with relationship

    started = db.Column(db.Boolean, nullable=False, default=False)
    starred = db.Column(db.Boolean, nullable=False, default=False)
    pinned = db.Column(db.Boolean, nullable=False, default=False)
    hidden = db.Column(db.Boolean, nullable=False, default=False)

    points = db.Column(db.Integer, nullable=False, default=0)
    last_visited = db.Column(db.DateTime, nullable=True)  # None for not visited
    last_changed = db.Column(db.Float, nullable=False)

    @classmethod
    def create(cls, user_id: int, course_id: int):
        if cls.find_by_ids(user_id, course_id) is not None:
            return None
        new_entry = cls(user_id=user_id, course_id=course_id, last_changed=datetime.utcnow().timestamp())
        db.session.add(new_entry)
        db.session.commit()
        return new_entry

    @classmethod
    def find_or_create(cls, user_id: int, course_id: int):
        entry = cls.query.filter_by(user_id=user_id, course_id=course_id).first()
        if entry is None:
            return cls.create(user_id, course_id)
        return entry

    @classmethod
    def find_json(cls, user_id: int, course_id: int) -> Dict[str, bool]:
        entry: cls = cls.find_by_ids(user_id, course_id)
        if entry is None:
            return dict.fromkeys(("hidden", "pinned", "starred", "started"), False)
        return entry.to_json()

    @classmethod
    def find_visit_date(cls, user_id: int, course_id: int) -> float:
        entry: cls = cls.find_by_ids(user_id, course_id)
        if entry is None:
            return -1
        return entry.get_visit_date()

    @classmethod
    def find_by_ids(cls, user_id: int, course_id: int):
        return cls.query.filter_by(user_id=user_id, course_id=course_id).first()

    @classmethod
    def filter_ids_by_user(cls, user_id: int, offset: int = None, limit: int = None, **params) -> List[int]:
        query: BaseQuery = cls.query.filter_by(user_id=user_id, **params)
        query = query.order_by(CourseSession.last_changed)

        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)

        return list(map(lambda x: x.course_id, query.all()))

    @classmethod
    def change_by_user(cls, user_id: int, operation: str, **params):
        course_session: CourseSession
        for course_session in cls.query.filter_by(user_id=user_id, **params).all():
            course_session.change_preference(operation)

    def is_valuable(self):
        return self.hidden or self.pinned or self.starred or self.started

    def to_json(self) -> Dict[str, bool]:
        return {
            "hidden": self.hidden, "pinned": self.pinned,
            "starred": self.starred, "started": self.started
        }

    def get_visit_date(self) -> float:
        return self.last_visited.timestamp() if self.last_visited is not None else -1

    def note_change(self):
        self.last_changed = datetime.utcnow().timestamp()
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


class Session(db.Model, Identifiable):  # try keeping in memory
    __tablename__ = "sessions"
    not_found_text = "Session not found"

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, nullable=False)
    module_id = db.Column(db.Integer, nullable=True)  # None outside any modules
    point_id = db.Column(db.Integer, nullable=True)  # None for non-standard modules

    test = db.Column(db.PickleType, nullable=True)  # None outside any test-modules
    user_id = db.Column(db.String, nullable=False)

    @classmethod
    def create(cls, user_id: int, course_id: int) -> Optional[int]:
        new_session = cls(user_id=user_id, course_id=course_id)
        db.session.add(new_session)
        db.session.commit()
        return new_session.id

    @classmethod
    def find_by_id(cls, entry_id: int):
        return cls.query.filter_by(id=entry_id).first()

    def collect(self):
        if self.point_id is None:
            return
        """
        user: User = User.find_by_id(self.user_id)
        session: CourseOldSession = user.get_course_session(self.course_id)

        if self.point_id == -1:
            session.complete_module(self.course_id, self.module_id)
        else:
            session.started_modules[self.module_id] = self.point_id

        user.update_course_session(self.course_id, session)"""

    def open_course(self, course_id: int):
        self.collect()  # collecting previous data
        self.course_id = course_id
        self.module_id = None
        self.point_id = None
        self.test = None
        db.session.commit()

    def open_module(self, module_id: int):
        self.collect()  # collecting previous data
        self.module_id = module_id
        self.point_id = None
        self.test = None

        pass  # CHECK FOR TEST AND START IT IF NEEDED

        db.session.commit()

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
