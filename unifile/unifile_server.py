from enum import Enum
from random import randint
from os.path import exists
from flask_cors import CORS
from math import sqrt, ceil
from os import path, urandom
from traceback import format_tb
from pickle import dumps, loads
from requests import Response, post
from base64 import urlsafe_b64encode
from email.mime.text import MIMEText
from flask_restful import Resource, Api
from googleapiclient.discovery import build
from subprocess import TimeoutExpired, call
from google.auth.exceptions import RefreshError
from passlib.hash import pbkdf2_sha256 as sha256
from flask_restful.reqparse import RequestParser
from google.oauth2.credentials import Credentials
from datetime import timezone, timedelta, datetime
from flask_sqlalchemy import SQLAlchemy, BaseQuery
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from itsdangerous import BadSignature as BS, URLSafeSerializer as USS
from typing import Union, Type, IO, List, Set, Tuple, Any, Dict, Callable, Optional
from flask import Response, jsonify, redirect, Flask, request, send_file, send_from_directory
from flask_jwt_extended import set_access_cookies, JWTManager, get_jwt, create_access_token,\
    unset_jwt_cookies, jwt_required, get_jwt_identity


versions: Dict[str, str] = {
    "API": "0.7.6",  # relates to everything in api_resources package
    "DBK": "0.6.3",  # relates to everything in database package
    "CAT": "0.3.5",  # relates to /cat/.../ resources
    "OCT": "0.2.8",  # relates to side thing (olympiad checker)
    "XiE": "-",  # relates to XiE webapp version (out of this project)
}

app: Flask = Flask(__name__)

app.config["SECRET_KEY"] = urandom(randint(32, 64))
app.config["SECURITY_PASSWORD_SALT"] = urandom(randint(32, 64))
app.config["PROPAGATE_EXCEPTIONS"] = True

app.config["JWT_TOKEN_LOCATION"] = ["cookies"]
app.config["JWT_COOKIE_CSRF_PROTECT"] = False
app.config["JWT_COOKIE_SAMESITE"] = "None"
app.config["JWT_COOKIE_SECURE"] = True
app.config["JWT_BLACKLIST_ENABLED"] = True
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=72)
app.config["JWT_BLACKLIST_TOKEN_CHECKS"] = ["access"]
app.config["JWT_SECRET_KEY"] = urandom(randint(32, 64))

app.config["MAIL_USERNAME"] = "xieffect.edu@gmail.com"


CORS(app, supports_credentials=True)  # , resources={r"/*": {"origins": "https://xieffect.vercel.app"}})

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db: SQLAlchemy = SQLAlchemy(app)


api: Api = Api(app)
jwt: JWTManager = JWTManager(app)


@app.before_first_request
def create_tables():
    db.create_all()

    Course.test()
    TestPoint.test()

    if User.find_by_email_address("test@test.test") is None:
        User.create("test@test.test", "test", "0a989ebc4a77b56a6e2bb7b19d995d185ce44090c" +
                    "13e2984b7ecc6d446d4b61ea9991b76a4c2f04b1b4d244841449454")
    if User.find_by_email_address("admin@admin.admin") is None:
        User.create("admin@admin.admin", "admin", "2b003f13e43546e8b416a9ff3c40bc4ba694d" +
                    "0d098a5a5cda2e522d9993f47c7b85b733b178843961eefe9cfbeb287fe")

    test_user: User = User.find_by_email_address("test@test.test")
    test_user.update_filters(Filters.test_filters())

    author = Author.find_by_id(test_user.id)
    if not author:
        print(1)
        author = Author.create(test_user.id)
        team = AuthorTeam.create("The TEST")
        team.courses.append(Course.find_by_id(3))
        team.courses.append(Course.find_by_id(12))
        team.courses.append(Course.find_by_id(13))
        author.teams.append(team)
        db.session.add(author)
        db.session.add(team)
        db.session.commit()


@jwt.token_in_blocklist_loader
def check_if_token_revoked(_, jwt_payload):
    return TokenBlockList.find_by_jti(jwt_payload["jti"]) is not None


@app.after_request
def refresh_expiring_jwt(response: Response):
    try:
        target_timestamp = datetime.timestamp(datetime.now(timezone.utc) + timedelta(hours=36))
        if target_timestamp > get_jwt()["exp"]:
            set_access_cookies(response, create_access_token(identity=get_jwt_identity()))
        return response
    except (RuntimeError, KeyError):
        return response


@app.errorhandler(Exception)
def on_any_exception(error: Exception):
    error_text = f"Requested URL: {request.path}\n" \
                 f"Error: {repr(error)}\n" + "".join(format_tb(error.__traceback__)[6:])
    response = send_discord_message(WebhookURLs.ERRORS, f"A server error appeared!\n```{error_text}```")
    if response.status_code < 200 or response.status_code > 299:
        send_discord_message(WebhookURLs.ERRORS,
                             f"Failed to report an error:\n```json\n{response.json()}```")
    return {"a": error_text}, 500


@jwt.expired_token_loader
def expired_token_callback(*_):
    return {"a": "expired token"}


@jwt.token_verification_failed_loader
def verification_failed_callback(*_):
    return {"a": f"token verification failed"}


@jwt.invalid_token_loader
def invalid_token_callback(callback):
    return {"a": f"invalid token: {callback}"}


@jwt.unauthorized_loader
def unauthorized_callback(callback):
    return {"a": f"unauthorized: {callback}"}


def update_available() -> bool:
    if exists(""):
        pass
    return False


def update() -> None:
    pass


def on_restart():
    send_discord_message(WebhookURLs.STATUS, "Application restated\nAPI version is " + versions["API"])
    if update_available():
        update()


class Filters:
    @classmethod
    def test_filters(cls):
        result = cls()
        result.binds = []
        result.hidden_courses = [18]
        result.started_courses = [0, 1, 2, 3]
        result.visit_datetimes = [
            datetime(2021, 3, 22, 17, 48, 0),
            datetime(1970, 3, 22, 17, 48, 0),
            datetime(2021, 2, 12, 12, 48, 0),
            datetime(2021, 3, 22, 17, 47, 59)
        ]
        result.starred_courses = [0, 2, 4, 12]
        result.pinned_courses = [0, 1, 5, 11]
        return result

    def __init__(self):
        self.binds: List[str] = list()
        self.hidden_courses: List[int] = list()
        self.pinned_courses: List[int] = list()
        self.starred_courses: List[int] = list()
        self.started_courses: List[int] = list()
        self.visit_datetimes: List[datetime] = list()

    def hide_course(self, code: int):
        self.hidden_courses.append(code)

    def unhide_course(self, code: int):
        if code in self.hidden_courses:
            self.hidden_courses.remove(code)

    def pin_course(self, code: int):
        self.pinned_courses.append(code)

    def unpin_course(self, code: int):
        if code in self.pinned_courses:
            self.pinned_courses.remove(code)

    def star_course(self, code: int):
        self.starred_courses.append(code)

    def unstar_course(self, code: int):
        if code in self.starred_courses:
            self.starred_courses.remove(code)

    def start_course(self, code: int):
        self.started_courses.append(code)
        self.visit_datetimes.append(datetime.utcnow())

    def update_binds(self, new_binds: List[str]) -> None:
        self.binds = new_binds

    def get_binds(self) -> List[str]:
        return self.binds

    def get_course_relation(self, course_id: int) -> Dict[str, bool]:
        return {"hidden": course_id in self.hidden_courses,
                "pinned": course_id in self.pinned_courses,
                "starred": course_id in self.starred_courses,
                "started": course_id in self.started_courses}

    def get_visit_date(self, code: int) -> float:
        try:
            i = self.started_courses.index(code)
            return self.visit_datetimes[i].timestamp()
        except ValueError:
            return -1


class Identifiable:
    not_found_text: str = ""

    def __init__(self, **kwargs):
        pass

    @classmethod
    def find_by_id(cls, entry_id: int):
        raise NotImplementedError


class UserRole:
    not_found_text: str = ""

    def __init__(self, **kwargs):
        pass

    @classmethod
    def find_by_id(cls, entry_id: int):
        raise NotImplementedError


class Point(db.Model):
    __tablename__ = "points"

    course_id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(db.Integer, primary_key=True)
    point_id = db.Column(db.Integer, primary_key=True)

    type = db.Column(db.Integer, nullable=False)  # 0 - Theory; 1 - HyperBlueprint
    data = db.Column(db.PickleType, nullable=False)  # List[int] (all used page ids)

    @classmethod
    def __create(cls, course_id: int, module_id: int, point_id: int, point_type: int, data: List[int]):
        if cls.find_by_ids(course_id, module_id, point_id):
            return False
        new_point = cls(course_id=course_id, module_id=module_id, point_id=point_id,
                        type=point_type, data=dumps(data))
        db.session.add(new_point)
        db.session.commit()
        return True

    @classmethod
    def find_by_ids(cls, course_id: int, module_id: int, point_id: int):
        return cls.query.filter_by(course_id=course_id, module_id=module_id, point_id=point_id).first()

    @classmethod
    def get_module_points(cls, course_id: int, module_id: int):
        return cls.query.filter_by(course_id=course_id, module_id=module_id).all()

    def execute(self) -> int:
        if self.type & 1:  # HyperBlueprint
            temp: List[int] = loads(self.data)
            return temp[randint(0, len(temp) - 1)]
        else:  # Theory
            pass


class Module(db.Model):
    __tablename__ = "modules"

    course_id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(db.Integer, primary_key=True)

    type = db.Column(db.Integer, nullable=False)  # 0 - standard; 1 - practice; 2 - theory; 3 - test
    name = db.Column(db.String(100), nullable=False)  # the name for the diagram (course map)
    length = db.Column(db.Integer, nullable=False)  # the amount of schedule or map points

    threshold = db.Column(db.Integer, nullable=False)  # points needed for starting
    parents = db.Column(db.PickleType, nullable=False)  # Set[int] (module ids in the same course)
    points = db.Column(db.Integer, nullable=False)  # points granted upon completion

    @classmethod
    def __create(cls, course_id: int, module_id: int, module_type: int, name: str,
                 length: int, threshold: int, parents: Set[int], points: int):
        if cls.find_by_ids(course_id, module_id):
            return False
        new_module = cls(course_id=course_id, module_id=module_id, type=module_type, name=name,
                         length=length, threshold=threshold, parents=dumps(parents), points=points)
        db.session.add(new_module)
        db.session.commit()
        return True

    @classmethod
    def find_by_ids(cls, course_id: int, module_id: int):
        return cls.query.filter_by(course_id=course_id, module_id=module_id).first()

    def is_access_granted(self, user_points: int, completed_modules: Set[int]) -> bool:
        if user_points < self.threshold:
            return False
        return loads(self.parents).issubset(completed_modules)


class Course(db.Model, Identifiable):  # same name courses are allowed
    @staticmethod
    def test():
        Course.__create(0, "Математика ЕГЭ", "", 4, "math", "une", "enthusiast",
                        2000, datetime(2020, 10, 22, 10, 30, 3))
        Course.__create(1, "стория ЕГЭ", "", 4, "history", "une", "enthusiast",
                        1100, datetime(2021, 1, 2, 22, 30, 33))
        Course.__create(2, "Арифметика", "", 4, "math", "middle-school", "newbie",
                        100, datetime(2012, 10, 12, 15, 57, 2))
        Course.__create(3, "Матан", "", 4, "math", "university", "amateur",
                        0, datetime(1999, 3, 14, 6, 10, 5))
        Course.__create(4, "English ABCs", "", 4, "languages", "hobby", "review",
                        2000, datetime(2019, 7, 22, 22, 10, 45))
        Course.__create(5, "Веб Дизайн", "", 4, "informatics", "prof-skills", "enthusiast",
                        2000, datetime(2020, 10, 22, 10, 30, 8))
        Course.__create(6, "Робототехника", "", 4, "informatics", "clubs", "newbie",
                        3100, datetime(2021, 1, 2, 22, 30, 33))
        Course.__create(7, "Архитектура XIX века", "", 4, "arts", "university", "expert",
                        5, datetime(2012, 6, 12, 15, 57, 0))
        Course.__create(8, "Безопасность в интернете", "", 4, "informatics", "university", "review",
                        2002, datetime(1999, 3, 14, 6, 10, 5))
        Course.__create(9, "Литература", "", 4, "literature", "bne", "enthusiast",
                        300, datetime(2019, 7, 12, 22, 10, 40))
        Course.__create(10, "Классическая Музыка", "", 4, "arts", "hobby", "enthusiast",
                        2000, datetime(2019, 3, 22, 22, 10, 40))
        Course.__create(11, "Немецкий язык", "", 4, "languages", "main-school", "enthusiast",
                        700, datetime(2015, 7, 22, 22, 10, 40))
        Course.__create(12, "География", "", 4, "geography", "hobby", "review",
                        2000, datetime(2019, 7, 22, 22, 1, 40))
        Course.__create(13, "Геодезия", "", 4, "geography", "hobby", "review",
                        2000, datetime(2016, 7, 22, 2, 52, 40))
        Course.__create(14, "Океанология", "", 4, "geography", "hobby", "review",
                        2000, datetime(2019, 7, 22, 22, 46, 40))
        Course.__create(15, "Ораторское искусство", "", 4, "arts", "prof-skills", "amateur",
                        1200, datetime(2009, 7, 22, 22, 31, 0))
        Course.__create(16, "Социология", "", 4, "social-science", "university", "review",
                        2000, datetime(2012, 6, 12, 15, 57, 0))
        Course.__create(17, "Классическая философия", "", 4, "philosophy", "hobby", "review",
                        700, datetime(2019, 7, 22, 22, 11, 40))
        Course.__create(18, "Физика: термодинамика", "", 4, "physics", "main-school", "review",
                        4200, datetime(2012, 7, 22, 2, 10, 54))
        Course.__create(19, "стория России", "", 4, "history", "hobby", "review",
                        270, datetime(2019, 7, 22, 22, 10, 24))
        Course.__create(20, "нформатика 7 класс", "", 4, "informatics", "middle-school", "amateur",
                        2000, datetime(2019, 7, 22, 22, 10, 12))
        Course.__create(21, "Литература Европы XX века", "", 4, "literature", "hobby", "review",
                        2000, datetime(2019, 5, 13, 1, 1, 54))
        Course.__create(22, "Python", "", 4, "informatics", "clubs", "newbie",
                        1500, datetime(2019, 7, 22, 22, 10, 32))

    __tablename__ = "courses"
    not_found_text = "Course not found"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    length = db.Column(db.Integer, nullable=False)

    theme = db.Column(db.String(20), nullable=False)
    category = db.Column(db.String(20), nullable=False)
    difficulty = db.Column(db.String(20), nullable=False)

    popularity = db.Column(db.Integer, nullable=False, default=100)
    creation_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    author_team = db.Column(db.Integer, db.ForeignKey("author-teams.id"), nullable=False,
                            default=0)  # test-only

    picture_type = db.Column(db.String(5), nullable=True, default="")
    module_map = db.Column(db.String(100), nullable=True, default="")  # test

    @classmethod
    def __create(cls, course_id: int, name: str, description: str, length: int, theme: str,
                 category: str, difficulty: str, popularity: int, creation_date: datetime) -> bool:
        if cls.find_by_id(course_id):
            return False
        new_course = cls(id=course_id, name=name, description=description, length=length,
                         theme=theme, category=category, difficulty=difficulty,
                         popularity=popularity, creation_date=creation_date)
        db.session.add(new_course)
        db.session.commit()
        return True

    @classmethod
    def find_by_id(cls, entry_id: int):
        return cls.query.filter_by(id=entry_id).first()

    @classmethod
    def get_course_list(cls, filters: Dict[str, List[str]], search: str,
                        user_filters: Filters, offset: int, limit: int) -> list:
        query: BaseQuery = cls.query

        query = query.filter(Course.id.notin_(user_filters.hidden_courses))

        if filters is not None:
            if "global" in filters.keys():
                global_filters = filters["global"]
                if "pinned" in global_filters:
                    query = query.filter(Course.id.in_(user_filters.pinned_courses))
                if "starred" in global_filters:
                    query = query.filter(Course.id.in_(user_filters.starred_courses))
                if "started" in global_filters:
                    query = query.filter(Course.id.in_(user_filters.started_courses))

            if "difficulty" in filters.keys() and len(filters["difficulty"]):
                query = query.filter(Course.difficulty.in_(filters["difficulty"]))
            if "category" in filters.keys() and len(filters["category"]):
                query = query.filter(Course.category.in_(filters["category"]))
            if "theme" in filters.keys() and len(filters["theme"]):
                query = query.filter(Course.theme.in_(filters["theme"]))

        if search is not None and len(search):
            query = query.filter(Course.name.like(f"%{search}%"))

        return query.offset(offset).limit(limit).all()

    def update_available_modules(self, user_points: int, completed_modules: Set[int],
                                 available_modules: Set[int]):
        for i in set(range(self.length)).difference(available_modules):
            module: Module = Module.find_by_ids(self.id, i)
            if module.is_access_granted(user_points, completed_modules):
                available_modules.add(i)

    def to_short_json(self) -> dict:
        return {"id": self.id, "name": self.name, "author": self.author_team}

    def to_json(self, user_filters: Filters = None) -> dict:
        result: dict = self.to_short_json()
        if user_filters is not None:
            result.update(user_filters.get_course_relation(self.id))
        result.update({"category": self.category, "theme": self.theme, "difficulty": self.difficulty})
        return result


class CourseSession:
    def __init__(self, goal_keys: List[str]):
        self.completed_modules: Set[int] = set()
        self.started_modules: Dict[int, int] = dict()
        self.available_modules: Set[int] = set()
        self.points: int = 0
        self.goals: Dict[str, int] = {key: 0 for key in goal_keys}

    def complete_module(self, course_id: int, module_id: int):
        self.completed_modules.add(module_id)
        self.started_modules.pop(module_id)
        self.available_modules.remove(module_id)

        course: Course = Course.find_by_id(course_id)
        course.update_available_modules(self.points, self.completed_modules, self.available_modules)


class ModerationStatus(Enum):
    POSTED = 0
    BEING_REVIEWED = 1
    DENIED = 2
    PUBLISHED = 3


class CATSubmission(db.Model, Identifiable):
    __tablename__ = "cat-submissions"
    not_found_text = "Submission not found"

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.Integer, nullable=False)  # 0 - page, 1 - course
    status = db.Column(db.Integer, nullable=False, default=0)  # ModerationStatus
    entity_id = db.Column(db.Integer, nullable=False)
    author_id = db.Column(db.String(100), nullable=False)
    date = db.Column(db.DateTime, nullable=False)

    @classmethod
    def create(cls, author_id: int, submission_type: int, tags: str):
        new_entry = cls(author_id=author_id, date=datetime.utcnow(),
                        type=submission_type, tags=tags)
        db.session.add(new_entry)
        db.session.commit()
        return new_entry

    @classmethod
    def find_by_id(cls, entry_id: int):
        return cls.query.filter_by(id=entry_id).first()

    @classmethod
    def find_by_tags(cls, tags: Set[str], submission_type: int = None,
                     offset: int = 0, limit: int = None):
        query: BaseQuery = cls.query.filter_by(status=ModerationStatus.POSTED.value)
        if submission_type is not None:
            query = query.filter_by(type=submission_type)

        for i in range(len(tags)):
            query = query.filter(CATSubmission.tags.like(f"%{tags.pop()} %"))
        query = query.order_by(CATSubmission.date)

        if limit is not None:
            query = query.limit(limit)
        return query.offset(offset).all()

    @classmethod
    def find_by_author(cls, author_id: int, offset: int, limit: int):
        return cls.query\
            .filter_by(author_id=author_id)\
            .order_by(CATSubmission.date)\
            .offset(offset).limit(limit).all()

    @classmethod
    def list_unreviewed(cls, offset: int, limit: int):
        return cls.query\
            .filter_by(status=ModerationStatus.POSTED.value)\
            .order_by(CATSubmission.date)\
            .offset(offset).limit(limit).all()

    def to_author_json(self) -> dict:
        return {"id": self.id, "status": self.status}

    def to_moderator_json(self) -> dict:
        return {"id": self.id, "type": self.type, "tags": self.tags}

    def mark_read(self) -> bool:
        if ModerationStatus(self.status) == ModerationStatus.POSTED:
            self.status = ModerationStatus.BEING_REVIEWED.value
            return True
        return False

    def delete(self) -> bool:
        if ModerationStatus(self.status) in (ModerationStatus.DENIED, ModerationStatus.PUBLISHED):
            db.session.delete(self)
            db.session.commit()
            return True
        return False

    def review(self, published: bool):
        if published:
            self.status = ModerationStatus.PUBLISHED.value
        else:
            self.status = ModerationStatus.DENIED.value


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

    def execute_point(self, point_id: Optional[int] = None) -> int:
        return self.point_id  # temp


association_table = db.Table(
    "teams",
    db.Column("author_id", db.Integer, db.ForeignKey("authors.id"), primary_key=True),
    db.Column("team_id", db.Integer, db.ForeignKey("author-teams.id"), primary_key=True)
)


class Author(db.Model, UserRole):
    __tablename__ = "authors"
    not_found_text = "Author does not exist"

    id = db.Column(db.Integer, primary_key=True)
    teams = db.relationship("AuthorTeam", secondary=association_table, back_populates="members")
    pages = db.relationship("Page", backref="authors")

    @classmethod
    def create(cls, user_id: int):
        new_entry = cls(id=user_id)
        db.session.add(new_entry)
        db.session.commit()
        return new_entry

    @classmethod
    def find_by_id(cls, entry_id: int):
        return cls.query.filter_by(id=entry_id).first()

    def get_teams(self, start: int = 0, finish: int = None) -> list:
        return list(map(lambda x: x.to_json(), self.teams[start:finish]))

    def get_wip_courses(self, start: int = 0, finish: int = None) -> list:
        pass

    def get_owned_pages(self, start: int = 0, finish: int = None) -> list:
        pass


class AuthorTeam(db.Model, Identifiable):
    __tablename__ = "author-teams"
    not_found_text = "Team does not exist"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    members = db.relationship("Author", secondary=association_table, back_populates="teams")
    courses = db.relationship("Course", backref="author-teams")
    wip_courses = db.relationship("CATCourse", backref="author-teams")

    @classmethod
    def find_by_id(cls, team_id):
        return cls.query.filter_by(id=team_id).first()

    @classmethod
    def create(cls, name: str):
        new_entry = cls(name=name)
        db.session.add(new_entry)
        db.session.commit()
        return new_entry

    def get_owned_courses(self, start: int = 0, finish: int = None) -> list:
        pass

    def to_json(self):
        return {"id": self.id, "name": self.name}


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

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), nullable=False, unique=True)
    email_confirmed = db.Column(db.Boolean, nullable=False, default=False)
    password = db.Column(db.String(100), nullable=False)

    username = db.Column(db.String(100), nullable=False)
    dark_theme = db.Column(db.Boolean, nullable=False, default=True)
    language = db.Column(db.String(20), nullable=False, default="russian")

    name = db.Column(db.String(100), nullable=True)
    surname = db.Column(db.String(100), nullable=True)
    patronymic = db.Column(db.String(100), nullable=True)

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


class Moderator(db.Model, UserRole):
    __tablename__ = "moderators"
    not_found_text = "Permission denied"

    id = db.Column(db.Integer, primary_key=True)

    @classmethod
    def find_by_id(cls, entry_id: int):
        return cls.query.filter_by(id=entry_id).first()

    @classmethod
    def create(cls, user_id: int) -> bool:
        if cls.find_by_id(user_id):
            return False
        new_entry = cls(id=user_id)
        db.session.add(new_entry)
        db.session.commit()
        return True


class Locations(Enum):
    SERVER = 0

    def to_link(self, file_type: str, file_id: int):
        result: str = ""
        if self == Locations.SERVER:
            result = f"/tfs/{file_type}/{file_id}/"

        return result


class CATFile(db.Model, Identifiable):
    __tablename__ = "cat-file_system"
    not_found_text = "File not found"

    id = db.Column(db.Integer, primary_key=True)
    owner = db.Column(db.String(100), db.ForeignKey("authors.id"), nullable=False,
                      default="")  # test-only
    location = db.Column(db.Integer, nullable=True)

    @classmethod
    def find_by_id(cls, entry_id: int):
        return cls.query.filter_by(id=entry_id).first()

    @classmethod
    def find_by_owner(cls, owner: Author) -> list:
        return cls.query.filter_by(owner=owner).all()

    def get_link(self):
        return Locations(self.location).to_link(self.__tablename__, self.id)


class CATCourse(CATFile):
    __tablename__ = "cat-courses"

    owner_team = db.Column(db.Integer, db.ForeignKey("author-teams.id"), nullable=False,
                           default=0)  # test-only
    pass


class Page(CATFile):
    __tablename__ = "pages"

    tags = db.Column(db.String(100), nullable=False)
    reusable = db.Column(db.Boolean, nullable=False)
    published = db.Column(db.Boolean, nullable=False)


class ResultCodes(Enum):
    TimeLimitExceeded = 4
    MemoryLimitExceeded = 3
    RuntimeError = 2
    WrongAnswer = 1
    Accepted = 0


class TestPoint(db.Model):
    @staticmethod
    def test():
        TestPoint.create("S1", 0, "4 6", "6", 10)
        TestPoint.create("S1", 1, "100 3", "100", 10)
        TestPoint.create("S1", 2, "0 0", "0", 10)
        for i in range(5):
            a: int = randint(0, 999)
            b: int = randint(0, 999)
            TestPoint.create("S1", i + 3, f"{a} {b}", str(max(a, b)), 10)
        TestPoint.create("S1", 8, "999999999 999999998", "999999999", 10)
        TestPoint.create("S1", 9, "999999999 999999999", "999999999", 10)

        temp: Dict[int, int] = {1: 1, 2: 1}
        f1, f2 = 1, 1
        for i in range(3, 1001):
            f1, f2 = f2, f1 + f2
            temp[i] = f2
        inputs = [1, 10, 4, 342, 312, 12, 32, 1000, 85, 829]
        for i in range(10):
            TestPoint.create("Q1", i, str(inputs[i]), str(temp[inputs[i]]), 10)

        def div_count(n):
            count = 2
            for i in range(2, ceil(sqrt(n))):
                if n % i == 0:
                    count += 2
            if sqrt(n) % 1 == 0:
                count += 1
            return count

        for i in range(9):
            if i == 5:
                TestPoint.create("P1", i, "1", "1", 14)
            elif i == 7:
                TestPoint.create("P1", i, "1000000", "49", 14)
            else:
                num = randint(2, 99999)
                TestPoint.create("P1", i, str(num), str(div_count(num)), 9)

    task_name = db.Column(db.String(2), primary_key=True)
    test_id = db.Column(db.Integer, primary_key=True)

    input = db.Column(db.Text, nullable=False)
    output = db.Column(db.Text, nullable=False)
    points = db.Column(db.Integer, nullable=False)

    @classmethod
    def find_by_task(cls, task_name: str) -> list:
        return cls.query.filter_by(task_name=task_name).all()

    @classmethod
    def find_exact(cls, task_name: str, test_id: int):
        return cls.query.filter_by(task_name=task_name, test_id=test_id).first()

    @classmethod
    def create(cls, task_name: str, test_id: int, inp: str, out: str, points: int):
        if cls.find_exact(task_name, test_id):
            return None
        new_test_point = cls(task_name=task_name, test_id=test_id, input=inp, output=out, points=points)
        db.session.add(new_test_point)
        db.session.commit()
        return new_test_point

    @classmethod
    def create_next(cls, task_name: str, inp: str, out: str, points: int) -> int:
        temp: list = cls.find_by_task(task_name)
        test_id: int = 0
        if len(temp):
            test_id = max(temp, key=lambda x: x.test_id).test_id + 1
        cls.create(task_name, test_id, inp, out, points)
        return test_id


class UserSubmissions(db.Model):
    user_id = db.Column(db.String(100), primary_key=True)
    task_name = db.Column(db.String(2), primary_key=True)
    id = db.Column(db.Integer, primary_key=True)

    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    code = db.Column(db.Integer, nullable=False)
    points = db.Column(db.Integer, nullable=False)
    failed = db.Column(db.Integer, nullable=False)

    @classmethod
    def find_group(cls, user_id: str, task_name: str) -> list:
        return cls.query.filter_by(user_id=user_id, task_name=task_name).all()

    @classmethod
    def find_exact(cls, user_id: str, task_name: str, submission_id: int):
        return cls.query.filter_by(user_id=user_id, task_name=task_name, id=submission_id).all()

    @classmethod
    def create(cls, user_id: str, task_name: str, submission_id: int, code: int, points: int, failed: int):
        if cls.find_exact(user_id, task_name, submission_id):
            return None
        new_submission = cls(user_id=user_id, task_name=task_name, code=code,
                             id=submission_id, points=points, failed=failed)
        db.session.add(new_submission)
        db.session.commit()
        return new_submission

    @classmethod
    def create_next(cls, user_id: str, task_name: str, code: int, points: int, failed: int):
        temp: list = cls.find_group(user_id, task_name)
        current_id: int = 0
        if len(temp):
            current_id = max(temp, key=lambda x: x.id).id + 1
        return cls.create(user_id, task_name, current_id, code, points, failed)

    def to_json(self) -> dict:
        return {
            "date": str(self.date),
            "code": ResultCodes(self.code).name,
            "points": self.points,
            "failed": self.failed
        }


counter_parser: RequestParser = RequestParser()
counter_parser.add_argument("counter", type=int, required=True)

password_parser: RequestParser = RequestParser()
password_parser.add_argument("password", required=True)


def jwt_authorizer(role: Type[UserRole], result_filed_name: Optional[str] = "user"):
    def authorizer_wrapper(function):
        @jwt_required()
        def authorizer_inner(*args, **kwargs):
            result: role = role.find_by_id(get_jwt_identity())
            if result is None:
                return {"a": role.not_found_text}, 401 if role is User else 403
            else:
                if result_filed_name is not None:
                    kwargs[result_filed_name] = result
                return function(*args, **kwargs)

        return authorizer_inner

    return authorizer_wrapper


def database_searcher(identifiable: Type[Identifiable], input_field_name: str,
                      result_filed_name: Optional[str] = None, check_only: bool = False):
    def searcher_wrapper(function):
        error_response: tuple = {"a": identifiable.not_found_text}, 404

        def searcher_inner(*args, **kwargs):
            target_id: int = kwargs.pop(input_field_name)
            result: identifiable = identifiable.find_by_id(target_id)
            if result is None:
                return error_response
            else:
                if result_filed_name is not None:
                    kwargs[result_filed_name] = result
                return function(*args, **kwargs)

        def checker_inner(*args, **kwargs):
            if identifiable.find_by_id(kwargs[input_field_name]) is None:
                return error_response
            else:
                return function(*args, **kwargs)

        if check_only:
            return checker_inner
        else:
            return searcher_inner

    return searcher_wrapper


def argument_parser(parser: RequestParser, *arg_names: Union[str, Tuple[str, str]]):
    def argument_wrapper(function):
        def argument_inner(*args, **kwargs):
            data: dict = parser.parse_args()
            for arg_name in arg_names:
                if isinstance(arg_name, str):
                    kwargs[arg_name] = data[arg_name]
                else:
                    kwargs[arg_name[1]] = data[arg_name[0]]
            return function(*args, **kwargs)

        return argument_inner

    return argument_wrapper


def lister(user_role: Type[UserRole], per_request: int, user_filed_name: Optional[str],
           argument_parser: Callable[[Callable], Any] = argument_parser(counter_parser, "counter")):
    def lister_wrapper(function):
        @jwt_authorizer(user_role)
        @argument_parser
        def lister_inner(*args, **kwargs):
            counter: int = kwargs.pop("counter") * per_request
            if user_filed_name is not None:
                kwargs[user_filed_name] = kwargs.pop("user")
            kwargs["start"] = counter
            kwargs["finish"] = counter + per_request
            return function(*args, **kwargs)

        return lister_inner

    return lister_wrapper


"""
https://discordapp.com/developers/docs/resources/webhook#execute-webhook
https://discordapp.com/developers/docs/resources/channel#embed-object

data = {"content": "message content", "username": "custom username", "embeds": []}
result: Response = requests.post(url, json=data, headers={"Content-Type": "application/json"})
"""


class WebhookURLs(Enum):
    COMPLAINER = "843249940390084628/fGSm8MItFd3-AqGHgJAY20NJzUPWfc0eJLE75dUJ09-Vhjjqe0gcBZ5W8lYre9yUIerS"
    STATUS = "843500826223312936/9ZcT7YinTBn4g0hdwPL_ca-YszwRUYrNrLhVEPjDrZQw_lMWHeo7l5LNtl6rq4LAUhgv"
    ERRORS = "843536959624445984/-V9-tEd9Af2mz-0L18YQqlabtK4rJatCSs0YS0XUFh-Tl-s49e2DG1Jg0z3wG2Soo0Op"
    WEIRDO = "843431829931556864/XY-k_4IOZ9NVatCuPEYB8OU6_DPSfUBP_lvGROf55g8GTM6TbDarcvLIJiz5KvGOZZZD"
    GITHUB = "853684564277592076/4aJk50o9-_XcRCD4dxOrh01NsAWQdCS20Q6_Akozwaw5x1gTBAPFahwiKiesjQUH1J8_"


def send_discord_message(webhook_url: WebhookURLs, message: str) -> Response:
    return post(f"https://discord.com/api/webhooks/{webhook_url.value}", json={"content": message})


email_folder: str = "emails/"
scopes: List[str] = ["https://mail.google.com/"]


class EmailSender:
    def __init__(self):
        self.credentials = Credentials.from_authorized_user_file("token.json", scopes) \
            if path.exists("token.json") else None
        self.service = None
        self.rebuild_service()
        self.sender = app.config["MAIL_USERNAME"]

    def rebuild_service(self):
        if not self.credentials or not self.credentials.valid:
            if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                self.credentials.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file("credentials.json", scopes)
                self.credentials = flow.run_local_server(port=0)
            with open("token.json", "w") as token:
                send_discord_message(WebhookURLs.WEIRDO, "Google API token has been re-written!")
                token.write(self.credentials.to_json())

        self.service = build("gmail", "v1", credentials=self.credentials)

    def generate_email(self, receiver: str, code: str, filename: str, theme: str):
        with open(email_folder + filename, "rb") as f:
            html: str = f.read().decode("utf-8").replace("&code", code)

        message = MIMEText(html, "html")
        message["to"] = receiver
        message["from"] = self.sender
        message["subject"] = theme

        return {"raw": urlsafe_b64encode(message.as_string().encode()).decode()}

    def generate_code_email(self, receiver: str, code_type: str, filename: str, theme: str):
        return self.generate_email(receiver, generate_code(receiver, code_type), filename, theme)

    def send(self, message):
        self.service.users().messages().send(userId="me", body=message).execute()


serializers: Dict[str, USS] = {k: USS(urandom(randint(32, 64))) for k in ["confirm", "change", "pass"]}
themes: Dict[str, str] = {
    "confirm": "Подтверждение адреса электронной почты на xieffect.ru",
    "change": "Смена адреса электронной почты на xieffect.ru",
    "pass": "Смена пароля на xieffect.ru"
}
salt: str = app.config["SECURITY_PASSWORD_SALT"]

try:
    sender: EmailSender = EmailSender()
except RefreshError as error:
    send_discord_message(WebhookURLs.ERRORS, "Google API token refresh failed again!")


def send_email(receiver: str, code: str, filename: str, theme: str):
    return sender.send(sender.generate_email(receiver, code, filename, theme))


def send_generated_email(receiver: str, code_type: str, filename: str):
    return sender.send(sender.generate_code_email(receiver, code_type, filename, themes[code_type]))


def generate_code(payload: str, code_type: str) -> str:
    return serializers[code_type].dumps(payload, salt=salt)


def parse_code(code: str, code_type: str) -> Optional[str]:
    try:
        return serializers[code_type].loads(code, salt=salt)
    except BS:
        return None


    send_generated_email("qwert45hi@yandex.ru", "confirm", "registration-email.html")


class TeamLister(Resource):  # [POST] /cat/teams/
    @lister(Author, 24, "author")
    def post(self, author: Author, start: int, finish: int) -> list:
        return author.get_teams(start, finish)


class OwnedCourseLister(Resource):  # [POST] /cat/courses/owned/
    parser: RequestParser = counter_parser.copy()
    parser.add_argument("team", type=int, required=True)

    @lister(Author, 24, "author", argument_parser(parser, "counter", ("team", "team_id")))
    @database_searcher(AuthorTeam, "team_id", "team")
    def post(self, author: Author, start: int, finish: int, team: AuthorTeam):
        if author not in team.members:
            return {"a": "Not a member"}, 403
        return team.get_owned_courses(start, finish)


class OwnedPageLister(Resource):  # [POST] /cat/pages/owned/
    @lister(Author, 24, "author")
    def post(self, author: Author, start: int, finish: int) -> list:
        return author.get_owned_pages(start, finish)


class ReusablePageLister(Resource):  # [POST] /cat/pages/reusable/
    parser: RequestParser = counter_parser.copy()
    parser.add_argument("tags", required=True)

    @lister(Author, 24, "author", argument_parser(parser, "counter", "tags"))
    def post(self, author: Author, start: int, finish: int, tags: str):
        pass


class CourseMapper(Resource):
    @jwt_authorizer(User)
    @database_searcher(Course, "course_id", "course")
    def get(self, user: User = None, course: Course = None):
        filters: Filters = user.get_filters()
        session_id: int = Session.create(user.id, course.id)

        result = course.to_json(filters)
        result.update({
            "session": session_id,
            "description": "Крутое описание курса!",
            "map": [
                {
                    "id": "0",
                    "type": "input",
                    "data": {
                        "label": "Введение"
                    },
                    "position": {
                        "x": 250,
                        "y": 5
                    },
                    "style": {
                        "background": "#357a38",
                        "color": "#e0e0e0",
                        "cursor": "pointer",
                        "border": "1px solid #777"
                    }
                },
                {
                    "id": "1",
                    "type": "output",
                    "data": {
                        "label": "Механика"
                    },
                    "position": {
                        "x": 100,
                        "y": 100
                    },
                    "style": {
                        "background": "#3f50b5",
                        "color": "#e0e0e0",
                        "cursor": "pointer",
                        "border": "1px solid #777"
                    }
                },
                {
                    "id": "2",
                    "type": "default",
                    "data": {
                        "label": "Электротехника"
                    },
                    "position": {
                        "x": 400,
                        "y": 100
                    },
                    "style": {
                        "background": "#3f50b5",
                        "color": "#e0e0e0",
                        "cursor": "pointer",
                        "border": "5px solid #357a38"
                    }
                },
                {
                    "id": "3",
                    "type": "output",
                    "data": {
                        "label": "Схемотехника"
                    },
                    "position": {
                        "x": 400,
                        "y": 200
                    },
                    "style": {
                        "background": "rgb(183, 28, 28, .8)",
                        "color": "#e0e0e0",
                        "cursor": "not-allowed",
                        "border": "1px solid #777"
                    }
                },
                {
                    "id": "interaction-e1-2",
                    "source": "0",
                    "target": "1"
                },
                {
                    "id": "interaction-e1-3",
                    "source": "0",
                    "target": "2"
                },
                {
                    "id": "interaction-e1-4",
                    "source": "2",
                    "target": "3"
                }
            ],
            "stats": [
                {
                    "value": 40,
                    "label": "Общий прогресс"
                },
                {
                    "value": 1,
                    "maximum": 3,
                    "label": "Завершено модулей"
                }
            ]
        })  # test
        return result


class SessionCourseMapper(Resource):  # /map/
    @jwt_authorizer(User, None)
    @database_searcher(Session, "session_id", "session")
    def get(self, session: Session):
        return redirect(f"/courses/{session.course_id}/map/")


class ModuleOpener(Resource):  # /modules/<ID>/
    @jwt_authorizer(User, None)
    @database_searcher(Session, "session_id", "session")
    def get(self, module_id: int, session: Session):
        session.open_module(module_id)
        return redirect(f"/pages/{session.next_page_id()}/")


class Progresser(Resource):  # /next/
    @jwt_authorizer(User, None)
    @database_searcher(Session, "session_id", "session")
    def post(self, session: Session):
        return redirect(f"/pages/{session.next_page_id()}/")


class Navigator(Resource):
    @jwt_authorizer(User, None)
    @database_searcher(Session, "session_id", "session")
    def get(self, point_id: int, session: Session):
        return redirect(f"/pages/{session.execute_point(point_id)}/")


class ContentsGetter(Resource):
    @jwt_authorizer(User, None)
    @database_searcher(Session, "session_id", "session")
    def get(self, session: Session):
        pass


class TestChecker(Resource):
    @jwt_authorizer(User, None)
    @database_searcher(Session, "session_id", "session")
    def post(self, session: Session):
        pass


class PageGetter(Resource):
    @jwt_authorizer(User, None)
    def get(self, page_id: int):
        if page_id == 0:
            pass
        elif page_id == 1:
            pass
        elif page_id == 2:
            pass
        elif page_id == 3:
            pass


class FilterGetter(Resource):  # [GET] /filters/
    @jwt_authorizer(User)
    def get(self, user: User):
        return user.get_filter_binds()


class SortType(str, Enum):
    POPULARITY = "popularity"
    VISIT_DATE = "visit-date"
    CREATION_DATE = "creation-date"


COURSES_PER_REQUEST: int = 12


class CourseLister(Resource):  # [POST] /courses/
    parser: RequestParser = counter_parser.copy()
    parser.add_argument("filters", type=dict, required=False)
    parser.add_argument("search", required=False)
    parser.add_argument("sort", required=False)

    @lister(User, 12, "user", argument_parser(parser, "counter", "filters", "search", "sort"))
    def post(self, user: User, start: int, finish: int, search: str,
             filters: Dict[str, List[str]], sort: str):
        user_filters: Filters = user.get_filters()

        try:
            if sort is None:
                sort: SortType = SortType.POPULARITY
            else:
                sort: SortType = SortType(sort)
        except ValueError:
            return {"a": f"Sorting '{sort}' is not supported"}, 406

        if filters is not None:
            if "global" in filters.keys():
                if "owned" in filters["global"]:  # TEMPORARY
                    return redirect("/cat/courses/owned/", 307)
                user_filters.update_binds(filters["global"])
            else:
                user_filters.update_binds(list())
            user.update_filters(user_filters)

        result: List[Course] = Course.get_course_list(
            filters, search, user_filters, start, finish-start)

        if sort == SortType.POPULARITY:
            result.sort(key=lambda x: x.popularity, reverse=True)
        elif sort == SortType.VISIT_DATE:
            result.sort(key=lambda x: (user_filters.get_visit_date(x.id), x.popularity), reverse=True)
        elif sort == SortType.CREATION_DATE:
            result.sort(key=lambda x: x.creation_date.timestamp(), reverse=True)

        return list(map(lambda x: x.to_json(user_filters), result))


class HiddenCourseLister(Resource):
    @lister(User, -12, "user")
    def post(self, user: User, start: int, finish: int) -> list:
        user_filters: Filters = user.get_filters()

        result = list()
        for course_id in user_filters.hidden_courses[finish:start if start != 0 else None]:
            course: Course = Course.find_by_id(course_id)
            result.append(course.to_short_json())
        return result


class CoursePreferences(Resource):  # [POST] /courses/<int:course_id>/preference/
    parser: RequestParser = RequestParser()
    parser.add_argument("a", required=True)

    @jwt_authorizer(User)
    @database_searcher(Course, "course_id", check_only=True)
    @argument_parser(parser, ("a", "operation"))
    def post(self, course_id: int, user: User, operation: str):
        filters: Filters = user.get_filters()

        if operation == "hide":
            filters.hide_course(course_id)
        elif operation == "show":
            filters.unhide_course(course_id)
        elif operation == "star":
            filters.star_course(course_id)
        elif operation == "unstar":
            filters.unstar_course(course_id)
        elif operation == "pin":
            filters.pin_course(course_id)
        elif operation == "unpin":
            filters.unpin_course(course_id)
        user.update_filters(filters)

        return {"a": True}


class CourseReporter(Resource):
    parser: RequestParser = RequestParser()
    parser.add_argument("reason", required=True)
    parser.add_argument("message", required=False)

    @jwt_authorizer(User, None)
    @database_searcher(Course, "course_id", "course")
    @argument_parser(parser, "reason", "message")
    def post(self, course: Course, reason: str, message: str):
        send_discord_message(
            WebhookURLs.COMPLAINER,
            f"Появилась новая жалоба на курс #{course.id} ({course.name})\n"
            f"Причина: {reason}" + f"\nСообщение: {message}" if message is not None else ""
        )
        return {"a": True}


class ShowAll(Resource):  # test
    @jwt_authorizer(User)
    def get(self, user: User):
        filters: Filters = user.get_filters()
        filters.hidden_courses = list()
        user.update_filters(filters)
        return {"a": True}


class Submitter(Resource):  # [POST] /cat/submissions/
    parser: RequestParser = RequestParser()
    parser.add_argument("type", type=int, required=True)
    parser.add_argument("tags", required=True)

    @jwt_authorizer(Author, "author")
    @argument_parser(parser, ("type", "submission_type"), "tags")
    def post(self, author: Author, submission_type: int, tags: str):
        submission: CATSubmission = CATSubmission.create(author.id, submission_type, tags)

        with open(f"submissions/s{submission.id}.json", "wb") as f:
            f.write(request.data)

        return {"a": "Success"}


class SubmissionLister(Resource):  # [POST] /cat/submissions/owned/
    @lister(Author, 24, "author")
    def post(self, author: Author, start: int, finish: int) -> list:
        submission: CATSubmission
        result: list = list()
        for submission in CATSubmission.find_by_author(author.id, start, finish - start):
            result.append(submission.to_author_json())
        return result


class SubmissionIndexer(Resource):  # [POST] /cat/submissions/index/
    parser: RequestParser = counter_parser.copy()
    parser.add_argument("type", type=int, required=False)
    parser.add_argument("tags", required=True)

    @lister(Moderator, 24, None, argument_parser(parser, "counter", ("type", "submission_type"), "tags"))
    def post(self, start: int, finish: int, submission_type: int, tags: str):
        submission: CATSubmission
        result: list = list()

        for submission in CATSubmission.find_by_tags(
                set(tags.split(" ")), submission_type, start, finish - start):
            result.append(submission.to_moderator_json())

        return result


class SubmissionReader(Resource):  # [GET] /cat/submissions/<int:submission_id>/
    @jwt_authorizer(Moderator, "moderator")
    @database_searcher(CATSubmission, "submission_id", "submission")
    def get(self, moderator: Moderator, submission: CATSubmission):
        pass  # check if taken

        submission.mark_read()

        return send_from_directory("submissions", f"s{submission.id}.json")


class ReviewIndex(Resource):  # [GET|POST] /cat/reviews/<int:submission_id>/
    parser: RequestParser = RequestParser()
    parser.add_argument("published", type=bool, required=True)

    @jwt_authorizer(Author, "author")
    @database_searcher(CATSubmission, "submission_id", "submission")
    def get(self, author: Author, submission: CATSubmission):
        if submission.author_id != author.id:
            return {"a": "'NOT YOUR STUFF' ERROR"}

        return send_from_directory("submissions", f"r{submission.id}.json")

    @argument_parser(parser, "published")
    @jwt_authorizer(Moderator, "moderator")
    @database_searcher(CATSubmission, "submission_id", "submission")
    def post(self, moderator: Moderator, submission: CATSubmission, published: bool):
        pass  # check if taken

        submission.review(published)

        with open(f"submissions/r{submission.id}.json", "wb") as f:
            f.write(request.data)


class Publisher(Resource):  # [POST] /cat/publications/
    @jwt_authorizer(Moderator, "moderator")
    def post(self, moderator: Moderator):
        pass


def file_getter(function):
    @jwt_authorizer(Author, "author")
    def get_file_or_type(file_type: str, *args, **kwargs):
        if file_type == "courses":
            result = CATCourse
        elif file_type == "pages":
            result = Page
        else:
            return {"a": f"File type '{file_type}' is not supported"}, 406

        if "file_id" in kwargs.keys():
            result = result.find_by_id(kwargs.pop("file_id"))
            return function(file=result, *args, **kwargs)
        else:
            return function(file_type=result, *args, **kwargs)

    return get_file_or_type


class FileLister(Resource):  # [POST] /wip/<file_type>/index/
    @file_getter
    @argument_parser(counter_parser, "counter")
    def post(self, file_type: Type[CATFile], author: Author, counter: int):
        pass


class FileProcessor(Resource):  # [GET|PUT|DELETE] /wip/<file_type>/<int:file_id>/
    @file_getter
    def get(self, author: Author, file: CATFile):
        pass

    @file_getter
    def put(self, author: Author, file: CATFile):
        pass

    @file_getter
    def delete(self, author: Author, file: CATFile):
        pass


class FileCreator(Resource):  # [POST] /wip/<file_type>/
    @file_getter
    def post(self, author: Author, file_type: Type[CATFile]):
        pass


class Version(Resource):
    def get(self, app_name: str):
        if app_name.upper() in versions.keys():
            return {"a": versions[app_name.upper()]}
        else:
            return {"a": "No such app"}, 400


class UploadAppUpdate(Resource):  # POST /<app_name>/
    @jwt_required()
    def post(self, app_name: str):
        if get_jwt_identity() != "admin@admin.admin":
            return {"a": "Access denied"}

        app_name = app_name.upper()
        if app_name == "OCT":
            with open("OlimpCheck.jar", "wb") as f:
                f.write(request.data)
            return {"a": "Success"}
        else:
            return {"a": "App update not supported"}


class HelloWorld(Resource):
    parser: RequestParser = RequestParser()
    parser.add_argument("test")

    def get(self):
        return {"hello": "word"}

    @jwt_authorizer(User)
    @argument_parser(parser, "test")
    def post(self, test: str, user: User):
        print(f"Got {test} in the field 'test', said hello")
        print(f"User, who asked was {user.email}")
        return {"hello": test}


class ServerMessenger(Resource):
    def get(self):
        return {"type": 2, "text": "Version: " + versions["API"]}


"""
import requests

position = requests.get('http://api.open-notify.org/iss-now.json').json()["iss_position"]
position = list(map(lambda x: float(x), position.values()))
try:
    return {"type": 2, "text": f"ISS coordinates: {position}."}
except KeyError:
    return {"type": 2, "text": "Couldn't track the ISS"}
"""


def check_one(inp: str, out: str) -> ResultCodes:
    fin: IO = open("oct/input", "wb")
    fin.write(inp.encode("utf-8"))
    fout: IO = open("oct/output", "wb")
    ferr: IO = open("oct/error", "wb")

    try:
        call(["python3", "oct/submission.py"], stdin=fin, stdout=fout, stderr=ferr, timeout=1)
    except TimeoutExpired:
        return ResultCodes.TimeLimitExceeded

    if path.exists("oct/error") and path.getsize("oct/error"):
        return ResultCodes.RuntimeError
    if not path.exists("oct/output"):
        return ResultCodes.WrongAnswer

    map(lambda x: x.close(), [fin, fout, ferr])

    with open("oct/output", "rb") as f:
        result: str = f.read().decode("utf-8")
    return ResultCodes.Accepted if result.split() == out.split() else ResultCodes.WrongAnswer


class SubmitTask(Resource):  # POST (JWT) /tasks/<task_name>/attempts/new/

    @jwt_authorizer(User)
    def post(self, task_name: str, user: User):
        if not TestPoint.find_by_task(task_name):
            return {"a": "Task doesn't exist"}

        with open("oct/submission.py", "wb") as f:
            f.write(request.data)

        test: TestPoint
        points: int = 0
        code: int = 0
        failed: int = -1

        for test in TestPoint.find_by_task(task_name):
            code = check_one(test.input, test.output).value
            if code == ResultCodes.Accepted.value:
                points += test.points
            else:
                failed = test.test_id
                break

        send_discord_message(WebhookURLs.WEIRDO, f"Hey, {user.email} just send in a task submission!\n"
                                         f"Task: {task_name}, code: {ResultCodes(code).name}, "
                                         f"points: {points}, failed after: {failed}")

        return UserSubmissions.create_next(user.id, task_name, code, points, failed).to_json()


class GetTaskSummary(Resource):  # GET (JWT) /tasks/<task_name>/attempts/all/
    @jwt_authorizer(User)
    def get(self, task_name: str, user: User):
        if not TestPoint.find_by_task(task_name):
            return {"a": "Task doesn't exist"}

        result: list = UserSubmissions.find_group(user.id, task_name)
        if not result:
            return []
        else:
            return list(map(lambda x: x.to_json(), result))


class UpdateRequest(Resource):  # /oct/update/
    def get(self):
        return send_file(r"OlimpCheck.jar")


pass  # api for creating remotely


class GithubWebhook(Resource):  # /update/
    parser: RequestParser = RequestParser()
    parser.add_argument("commits", dict)
    parser.add_argument("X-GitHub-Event", str, location="headers")

    @argument_parser(parser, ("X-GitHub-Event", "event_type"), "commits")
    def post(self, event_type: str, commits: dict):
        if event_type == "push":
            version: str = commits["message"]
            send_discord_message(WebhookURLs.STATUS, f"New API version {version} uploaded!")
        elif event_type == "release":
            send_discord_message(WebhookURLs.GITHUB, f"Got a {event_type} notification.\n"
                                                     f"Releases are not supported yet!")
        else:
            send_discord_message(WebhookURLs.GITHUB, f"Got a {event_type} notification.\n"
                                                     f"No action was applied.")


class EmailSender(Resource):
    def post(self, email: str):
        user: User = User.find_by_email_address(email)
        if user is None:
            return {"a": User.not_found_text}, 404
        if user.email_confirmed:
            return {"a": "Confirmed"}

        send_generated_email(email, "confirm", "registration-email.html")
        return {"a": "Success"}


class EmailConfirm(Resource):
    parser: RequestParser = RequestParser()
    parser.add_argument("code", required=True)

    @argument_parser(parser, "code")
    def post(self, code: str):
        email = parse_code(code, "confirm")
        if email is None:
            return {"a": "Code error"}

        user: User = User.find_by_email_address(email)
        if user is None:
            return {"a": User.not_found_text}, 404

        user.confirm_email()
        return {"a": "Success"}


class UserRegistration(Resource):
    parser = password_parser.copy()
    parser.add_argument("email", required=True)
    parser.add_argument("username", required=True)

    @argument_parser(parser, "email", "username", "password")
    def post(self, email: str, username: str, password: str):
        user: User = User.create(email, username, password)
        if not user:
            return {"a": False}

        send_generated_email(email, "confirm", "registration-email.html")

        response = jsonify({"a": True})
        set_access_cookies(response, create_access_token(identity=user.id))
        return response


class UserLogin(Resource):
    parser: RequestParser = password_parser.copy()
    parser.add_argument("email", required=True, help="email is required")

    @argument_parser(parser, "email", "password")
    def post(self, email: str, password: str):

        user: User = User.find_by_email_address(email)
        if not user:
            return {"a": "User doesn't exist"}

        if User.verify_hash(password, user.password):
            response: Response = jsonify({"a": "Success"})
            set_access_cookies(response, create_access_token(identity=user.id))
            return response
        else:
            return {"a": "Wrong password"}


class UserLogout(Resource):
    @jwt_required()
    def post(self):
        response = jsonify({"a": True})
        TokenBlockList.add_by_jti(get_jwt()["jti"])
        unset_jwt_cookies(response)
        return response


class PasswordResetSender(Resource):
    def get(self, email: str):
        if not User.find_by_email_address(email) or email == "admin@admin.admin":
            return {"a": False}
        send_generated_email(email, "pass", "password-reset-email.html")
        return {"a": True}


class PasswordReseter(Resource):
    parser: RequestParser = password_parser.copy()
    parser.add_argument("code", required=True)

    @argument_parser(parser, "code", "password")
    def post(self, code: str, password: str):
        email = parse_code(code, "pass")
        if email is None:
            return {"a": "Code error"}

        user: User = User.find_by_email_address(email)
        if not user:
            return {"a": "User doesn't exist"}

        user.change_password(password)
        return {"a": "Success"}


class Avatar(Resource):
    @jwt_authorizer(User)
    def get(self, user: User):
        return send_from_directory("avatars", f"{user.id}.png")

    @jwt_authorizer(User)
    def post(self, user: User):
        with open(f"avatars/{user.id}.png", "wb") as f:
            f.write(request.data)
        return {"a": True}


class Settings(Resource):
    parser: RequestParser = RequestParser()
    parser.add_argument("changed", type=dict, location="json", required=True)

    @jwt_authorizer(User)
    def get(self, user: User):
        return user.get_settings()

    @jwt_authorizer(User)
    @argument_parser(parser, "changed")
    def post(self, user: User, changed: dict):
        user.change_settings(changed)
        return {"a": True}


class MainSettings(Resource):
    @jwt_authorizer(User)
    def get(self, user: User):
        return user.get_main_settings()


class EmailChanger(Resource):
    parser: RequestParser = password_parser.copy()
    parser.add_argument("new-email", required=True)

    @jwt_authorizer(User)
    @argument_parser(parser, "password", ("new-email", "new_email"))
    def post(self, user: User, password: str, new_email: str):
        if not User.verify_hash(password, user.password):
            return {"a": "Wrong password"}

        if User.find_by_email_address(new_email):
            return {"a": "Email in use"}

        send_generated_email(new_email, "confirm", "registration-email.html")
        user.change_email(new_email)
        return {"a": "Success"}


class PasswordChanger(Resource):
    parser: RequestParser = password_parser.copy()
    parser.add_argument("new-password", required=True)

    @jwt_authorizer(User)
    @argument_parser(parser, "password", ("new-password", "new_password"))
    def post(self, user: User, password: str, new_password: str):
        if User.verify_hash(password, user.password):
            user.change_password(new_password)
            return {"a": "Success"}
        else:
            return {"a": "Wrong password"}


api.add_resource(HelloWorld, "/", )
api.add_resource(ServerMessenger, "/status/")
api.add_resource(EmailSender, "/email/<email>/")
api.add_resource(EmailConfirm, "/email-confirm/")
api.add_resource(UserRegistration, "/reg/")
api.add_resource(UserLogin, "/auth/")
api.add_resource(UserLogout, "/logout/")
api.add_resource(PasswordResetSender, "/password-reset/<email>/")
api.add_resource(PasswordReseter, "/password-reset/confirm/")
api.add_resource(Avatar, "/avatar/")
api.add_resource(Settings, "/settings/")
api.add_resource(MainSettings, "/settings/main/")
api.add_resource(EmailChanger, "/email-change/")
api.add_resource(PasswordChanger, "/password-change/")
api.add_resource(FilterGetter, "/filters/")
api.add_resource(CourseLister, "/courses/")
api.add_resource(HiddenCourseLister, "/courses/hidden/")
api.add_resource(CoursePreferences, "/courses/<int:course_id>/preference/")
api.add_resource(CourseReporter, "/courses/<int:course_id>/report/")
api.add_resource(CourseMapper, "/courses/<int:course_id>/map/")
api.add_resource(SessionCourseMapper, "/sessions/<int:session_id>/map/")
api.add_resource(ModuleOpener, "/sessions/<int:session_id>/modules/<int:module_id>/")
api.add_resource(Progresser, "/sessions/<int:session_id>/next/")
api.add_resource(Navigator, "/sessions/<int:session_id>/points/<int:point_id>/")
api.add_resource(ContentsGetter, "/sessions/<int:session_id>/contents/")
api.add_resource(TestChecker, "/sessions/<int:session_id>/submit/")
api.add_resource(TeamLister, "/cat/teams/")
api.add_resource(OwnedCourseLister, "/cat/courses/owned/")
api.add_resource(OwnedPageLister, "/cat/pages/owned/")
api.add_resource(ReusablePageLister, "/cat/pages/reusable/")
api.add_resource(Submitter, "/cat/submissions/")
api.add_resource(SubmissionLister, "/cat/submissions/owned/")
api.add_resource(SubmissionIndexer, "/cat/submissions/index/")
api.add_resource(SubmissionReader, "/cat/submissions/<int:submission_id>/")
api.add_resource(ReviewIndex, "/cat/reviews/<int:submission_id>/")
api.add_resource(Publisher, "/cat/publications/")
api.add_resource(PageGetter, "/pages/<int:page_id>/")
api.add_resource(Version, "/<app_name>/version/")
api.add_resource(GithubWebhook, "/update/")
api.add_resource(UpdateRequest, "/oct/update/")
api.add_resource(SubmitTask, "/tasks/<task_name>/attempts/new/")
api.add_resource(GetTaskSummary, "/tasks/<task_name>/attempts/all/")
api.add_resource(ShowAll, "/test/")

if __name__ == "__main__":
    app.run(debug=True)
