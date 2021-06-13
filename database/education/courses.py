from datetime import datetime
from pickle import dumps, loads
from random import randint
from typing import Dict, List, Set

from flask_sqlalchemy import BaseQuery

from database.base.addons import Filters
from database.base.basic import Identifiable
from main import db


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

    # Vital stuff:
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    length = db.Column(db.Integer, nullable=False)

    # Filtering:
    theme = db.Column(db.String(20), nullable=False)
    category = db.Column(db.String(20), nullable=False)
    difficulty = db.Column(db.String(20), nullable=False)

    # Sorting:
    popularity = db.Column(db.Integer, nullable=False, default=100)
    creation_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Author-related
    author_team = db.Column(db.Integer, db.ForeignKey("author-teams.id"), nullable=False,
                            default=0)  # test-only

    # File-related:
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
