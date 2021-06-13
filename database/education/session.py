from typing import Optional

from database.education.courses import CourseSession
from database.users.users import User
from database.base.basic import Identifiable
from main import db


class Session(db.Model, Identifiable):  # try keeping in memory
    __tablename__ = "sessions"
    not_found_text = "Session not found"

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, nullable=False, unique=False)
    module_id = db.Column(db.Integer, nullable=True, unique=False)  # None outside any modules
    point_id = db.Column(db.Integer, nullable=True, unique=False)  # None for non-standard modules

    test = db.Column(db.PickleType, nullable=True, unique=False)  # None outside any test-modules
    user_id = db.Column(db.String, nullable=False, unique=False)

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

        user: User = User.find_by_id(self.user_id)
        session: CourseSession = user.get_course_session(self.course_id)

        if self.point_id == -1:
            session.complete_module(self.course_id, self.module_id)
        else:
            session.started_modules[self.module_id] = self.point_id

        user.update_course_session(self.course_id, session)

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
