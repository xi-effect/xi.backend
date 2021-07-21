from datetime import datetime
from enum import Enum
from pickle import dumps, loads
from random import randint
from typing import Dict, List

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
    def __create(cls, module_type: ModuleType, name: str, length: int):
        new_module = cls(type=module_type.value, name=name, length=length)
        db.session.add(new_module)
        db.session.commit()
        return True

    @classmethod
    def find_by_id(cls, module_id: int):
        return cls.query.filter_by(id=module_id).first()

    @classmethod
    def get_module_list(cls, filters: Dict[str, str], user_id: int, offset: int, limit: int) -> list:
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
