from datetime import datetime
from enum import Enum
from pickle import dumps, loads
from random import randint
from typing import Dict, List, Optional

from flask_sqlalchemy import BaseQuery

from componets import Identifiable
from education.sessions import ModuleFilterSession
from main import db


class Point(db.Model):
    __tablename__ = "points"

    module_id = db.Column(db.Integer, primary_key=True)
    point_id = db.Column(db.Integer, primary_key=True)

    type = db.Column(db.Integer, nullable=False)  # 0 - Theory; 1 - HyperBlueprint
    data = db.Column(db.PickleType, nullable=False)  # do a relation!

    @classmethod
    def __create(cls, module_id: int, point_id: int, point_type: int, data: List[int]):
        if cls.find_by_ids(module_id, point_id):
            return False
        new_point = cls(module_id=module_id, point_id=point_id, type=point_type, data=dumps(data))
        db.session.add(new_point)
        db.session.commit()
        return True

    @classmethod
    def find_by_ids(cls, module_id: int, point_id: int):
        return cls.query.filter_by(module_id=module_id, point_id=point_id).first()

    @classmethod
    def find_and_execute(cls, module_id: int, point_id: int) -> int:
        entry: cls = cls.find_by_ids(module_id, point_id)
        return entry.execute()

    @classmethod
    def get_module_points(cls, module_id: int):
        return cls.query.filter_by(module_id=module_id).all()

    def execute(self) -> int:
        if self.type & 1:  # HyperBlueprint
            temp: List[int] = loads(self.data)
            return temp[randint(0, len(temp) - 1)]
        else:  # Theory
            pass


class ModuleType(Enum):
    STANDARD = 0
    PRACTICE_BLOCK = 1
    THEORY_BLOCK = 2
    TEST = 3


class Module(db.Model, Identifiable):
    @staticmethod
    def create_test_bundle():
        if Module.find_by_id(0):
            return
        Module.__create(0, ModuleType.TEST, "Пробник математика ЕГЭ", 4, "math", "une", "enthusiast", 2000,
                        datetime(2020, 10, 22, 10, 30, 3))
        Module.__create(1, ModuleType.THEORY_BLOCK, "История: теория для ЕГЭ", 4, "history", "une", "enthusiast", 1100,
                        datetime(2021, 1, 2, 22, 30, 33))
        Module.__create(2, ModuleType.STANDARD, "Арифметика", 4, "math", "middle-school", "newbie", 100,
                        datetime(2012, 10, 12, 15, 57, 2))
        Module.__create(3, ModuleType.PRACTICE_BLOCK, "100 упражнений по матану", 4, "math", "university", "amateur", 0,
                        datetime(1999, 3, 14, 6, 10, 5))
        Module.__create(4, ModuleType.STANDARD, "English ABCs", 4, "languages", "hobby", "review", 2000,
                        datetime(2019, 7, 22, 22, 10, 45))
        Module.__create(5, ModuleType.STANDARD, "Веб Дизайн", 4, "informatics", "prof-skills", "enthusiast", 2000,
                        datetime(2020, 10, 22, 10, 30, 8))
        Module.__create(6, ModuleType.STANDARD, "Робототехника", 4, "informatics", "clubs", "newbie", 3100,
                        datetime(2021, 1, 2, 22, 30, 33))
        Module.__create(7, ModuleType.TEST, "Архитектура XIX века", 4, "arts", "university", "expert", 5,
                        datetime(2012, 6, 12, 15, 57, 0))
        Module.__create(8, ModuleType.STANDARD, "Безопасность в интернете", 4, "informatics", "university", "review",
                        2002, datetime(1999, 3, 14, 6, 10, 5))
        Module.__create(9, ModuleType.THEORY_BLOCK, "Литература", 4, "literature", "bne", "enthusiast", 300,
                        datetime(2019, 7, 12, 22, 10, 40))
        Module.__create(10, ModuleType.THEORY_BLOCK, "Классическая Музыка", 4, "arts", "hobby", "enthusiast", 2000,
                        datetime(2019, 3, 22, 22, 10, 40))
        Module.__create(11, ModuleType.STANDARD, "Немецкий язык", 4, "languages", "main-school", "enthusiast", 700,
                        datetime(2015, 7, 22, 22, 10, 40))
        Module.__create(12, ModuleType.PRACTICE_BLOCK, "География: контурные карты", 4, "geography", "hobby", "review",
                        2000, datetime(2019, 7, 22, 22, 1, 40))
        Module.__create(13, ModuleType.STANDARD, "Геодезия", 4, "geography", "hobby", "review", 2000,
                        datetime(2016, 7, 22, 2, 52, 40))
        Module.__create(14, ModuleType.STANDARD, "Океанология", 4, "geography", "hobby", "review", 2000,
                        datetime(2019, 7, 22, 22, 46, 40))
        Module.__create(15, ModuleType.TEST, "Ораторское искусство", 4, "arts", "prof-skills", "amateur", 1200,
                        datetime(2009, 7, 22, 22, 31, 0))
        Module.__create(16, ModuleType.THEORY_BLOCK, "Социология", 4, "social-science", "university", "review", 2000,
                        datetime(2012, 6, 12, 15, 57, 0))
        Module.__create(17, ModuleType.STANDARD, "Классическая философия", 4, "philosophy", "hobby", "review", 700,
                        datetime(2019, 7, 22, 22, 11, 40))
        Module.__create(18, ModuleType.STANDARD, "Физика: термодинамика", 4, "physics", "main-school", "review", 4200,
                        datetime(2012, 7, 22, 2, 10, 54))
        Module.__create(19, ModuleType.PRACTICE_BLOCK, "История России", 4, "history", "hobby", "review", 270,
                        datetime(2019, 7, 22, 22, 10, 24))
        Module.__create(20, ModuleType.STANDARD, "Информатика 7 класс", 4, "informatics", "middle-school", "amateur",
                        2000, datetime(2019, 7, 22, 22, 10, 12))
        Module.__create(21, ModuleType.TEST, "Литература Европы XX века", 4, "literature", "hobby", "review", 2000,
                        datetime(2019, 5, 13, 1, 1, 54))
        Module.__create(22, ModuleType.PRACTICE_BLOCK, "Python", 4, "informatics", "clubs", "newbie", 1500,
                        datetime(2019, 7, 22, 22, 10, 32))

    __tablename__ = "modules"
    not_found_text = "Module not found"

    # Essentials
    id = db.Column(db.Integer, primary_key=True)
    length = db.Column(db.Integer, nullable=False)  # the amount of schedule or map points
    type = db.Column(db.Integer, nullable=False)  # 0 - standard; 1 - practice; 2 - theory; 3 - test
    name = db.Column(db.String(100), nullable=False)  # the name for the diagram (course map)

    # Filtering:
    theme = db.Column(db.String(20), nullable=False)
    category = db.Column(db.String(20), nullable=False)
    difficulty = db.Column(db.String(20), nullable=False)

    # Sorting:
    popularity = db.Column(db.Integer, nullable=False, default=100)
    creation_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Author-related
    author = db.Column(db.Integer, db.ForeignKey("authors.id"), nullable=False,
                       default=0)

    @classmethod
    def __create(cls, module_id: int, module_type: ModuleType, name: str, length: int, theme: str,
                 category: str, difficulty: str, popularity: int, creation_date: datetime = None):
        if creation_date is None:
            creation_date = datetime.utcnow()
        new_module = cls(id=module_id, type=module_type.value, name=name, length=length,
                         theme=theme, category=category, difficulty=difficulty,
                         popularity=popularity, creation_date=creation_date)
        db.session.add(new_module)
        db.session.commit()
        return True

    @classmethod
    def find_by_id(cls, module_id: int):
        return cls.query.filter_by(id=module_id).first()

    @classmethod
    def get_module_list(cls, filters: Optional[Dict[str, str]], user_id: int, offset: int, limit: int) -> list:
        query: BaseQuery = cls.query
        # explore joining queries!
        query = query.filter(cls.id.notin_(ModuleFilterSession.filter_ids_by_user(user_id, hidden=True)))

        if filters is not None:
            keys: List[str] = list(filters.keys())
            if "global" in keys:
                global_filter: str = filters["global"]
                if global_filter == "pinned":
                    # joining queries!
                    query = query.filter(cls.id.in_(ModuleFilterSession.filter_ids_by_user(user_id, pinned=True)))
                elif global_filter == "starred":
                    query = query.filter(cls.id.in_(ModuleFilterSession.filter_ids_by_user(user_id, starred=True)))
                elif global_filter == "started":
                    query = query.filter(cls.id.in_(ModuleFilterSession.filter_ids_by_user(user_id, started=True)))

            if "difficulty" in keys:
                query = query.filter_by(difficulty=filters["difficulty"])
            if "category" in keys:
                query = query.filter_by(category=filters["category"])
            if "theme" in keys:
                query = query.filter_by(theme=filters["theme"])

        return query.offset(offset).limit(limit).all()

    def get_any_point(self) -> Point:
        return Point.find_by_ids(self.id, randint(1, self.length))

    def to_short_json(self) -> dict:
        return {"id": self.id, "name": self.name, "author": self.author}

    def to_json(self, user_id: int = None) -> dict:
        result: dict = self.to_short_json()
        if user_id is not None:
            result.update(ModuleFilterSession.find_json(user_id, self.id))
        result.update({"theme": self.theme, "difficulty": self.difficulty, "category": self.category,
                       "type": ModuleType(self.type).name.lower().replace("_", "-")})
        return result