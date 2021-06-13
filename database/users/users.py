from pickle import dumps, loads
from typing import Dict, Union, List

from passlib.hash import pbkdf2_sha256 as sha256

from database.base.addons import Filters
from database.base.basic import UserRole
from database.education.courses import CourseSession
from database.users.special import Moderator
from main import db


class TokenBlockList(db.Model):
    id = db.Column(db.Integer, primary_key=True, unique=True)
    jti = db.Column(db.String(36), nullable=False)

    @classmethod
    def find_by_jti(cls, jti):
        return db.session.query(TokenBlockList.id).filter_by(jti=jti).scalar()

    @classmethod
    def add_by_jti(cls, jti):
        db.session.add(TokenBlockList(jti=jti))
        db.session.commit()


class User(db.Model, UserRole):
    __tablename__ = "users"
    not_found_text = "User does not exist"

    @staticmethod
    def generate_hash(password):
        return sha256.hash(password)

    @staticmethod
    def verify_hash(password, hashed):
        return sha256.verify(password, hashed)

    # Vital:
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), nullable=False, unique=True)
    email_confirmed = db.Column(db.Boolean, nullable=False, default=False)
    password = db.Column(db.String(100), nullable=False)

    # Settings:
    username = db.Column(db.String(100), nullable=False)
    dark_theme = db.Column(db.Boolean, nullable=False, default=True)
    language = db.Column(db.String(20), nullable=False, default="russian")

    # Real name:
    name = db.Column(db.String(100), nullable=True)
    surname = db.Column(db.String(100), nullable=True)
    patronymic = db.Column(db.String(100), nullable=True)

    # Education data:
    filters = db.Column(db.PickleType, nullable=False)  # Filters
    course_sessions = db.Column(db.PickleType, nullable=False)  # Dict[int, CourseSession]

    @classmethod
    def find_by_id(cls, entry_id: int):
        return cls.query.filter_by(id=entry_id).first()

    @classmethod
    def find_by_email_address(cls, email):
        return cls.query.filter_by(email=email).first()

    @classmethod
    def create(cls, email: str, username: str, password: str):
        if cls.find_by_email_address(email):
            return None
        new_user = cls(email=email, password=cls.generate_hash(password), username=username,
                       filters=dumps(Filters()), course_sessions=dumps(dict()))
        db.session.add(new_user)
        db.session.commit()
        return new_user

    def confirm_email(self):
        self.email_confirmed = True
        db.session.commit()

    def change_email(self, new_email: str) -> bool:
        if User.find_by_email_address(new_email):
            return False
        self.email = new_email
        self.email_confirmed = False
        db.session.commit()
        return True

    def change_password(self, new_password: str):
        self.password = User.generate_hash(new_password)
        db.session.commit()

    def change_settings(self, new_values: Dict[str, Union[str, int, bool]]):
        if "username" in new_values.keys():
            self.username = new_values["username"]
        if "dark-theme" in new_values.keys():
            self.dark_theme = new_values["dark-theme"]
        if "language" in new_values.keys():
            self.language = new_values["language"]
        if "name" in new_values.keys():
            self.name = new_values["name"]
        if "surname" in new_values.keys():
            self.surname = new_values["surname"]
        if "patronymic" in new_values.keys():
            self.patronymic = new_values["patronymic"]
        db.session.commit()

    def get_main_settings(self) -> Dict[str, str]:
        return {
            "username": self.username, "moderator": Moderator.find_by_id(self.id) is not None,
            "dark-theme": self.dark_theme, "language": self.language
        }

    def get_settings(self) -> Dict[str, str]:
        return {
            "email": self.email, "email-confirmed": self.email_confirmed, "username": self.username,
            "name": self.name, "surname": self.surname, "patronymic": self.patronymic,
            "dark-theme": self.dark_theme, "language": self.language
        }

    def get_filters(self) -> Filters:
        return loads(self.filters)

    def update_filters(self, filters: Filters) -> None:
        self.filters = dumps(filters)
        db.session.commit()

    def get_filter_binds(self) -> List[str]:
        return self.get_filters().get_binds()

    def get_course_relation(self, course_id: int) -> Dict[str, bool]:
        return self.get_filters().get_course_relation(course_id)

    def get_course_sessions(self) -> Dict[int, CourseSession]:
        return loads(self.course_sessions)

    def update_course_sessions(self, data: Dict[int, CourseSession]) -> None:
        self.course_sessions = dumps(data)
        db.session.commit()

    def get_course_session(self, course_id) -> CourseSession:
        return loads(self.course_sessions[course_id])

    def update_course_session(self, course_id: int, session: CourseSession) -> None:
        sessions: Dict[int, CourseSession] = self.get_course_sessions()
        sessions[course_id] = session
        self.course_sessions = dumps(sessions)
        db.session.commit()
