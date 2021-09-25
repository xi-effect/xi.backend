from datetime import datetime
from enum import Enum
from json import dumps as json_dumps, loads as json_loads, load
from pickle import dumps, loads
from random import randint
from typing import Dict, List, Optional, Union

from sqlalchemy import Column, ForeignKey, select
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import Integer, String, Boolean, JSON, DateTime, PickleType, Text

from authorship import Author
from componets import Identifiable
from componets.checkers import first_or_none
from education.sessions import ModuleFilterSession
from main import Base, Session, whooshee


class PageKind(Enum):
    THEORY = 0
    PRACTICE = 1
    TASK = 2

    @classmethod
    def from_string(cls, string):
        return cls.__members__[string.upper()]


@whooshee.register_model("name", "theme", "description")
class Page(Base, Identifiable):
    @staticmethod
    def create_test_bundle(session: Session, author: Author):
        for i in range(1, 4):
            with open(f"../files/tfs/test/{i}.json", "rb") as f:
                Page.create(session, load(f), author)

    __tablename__ = "pages"
    not_found_text = "Page not found"
    directory = "files/tfs/cat-pages/"

    id = Column(Integer, primary_key=True)
    author_id = Column(Integer, ForeignKey("authors.id"), nullable=False)
    author = relationship("Author")
    components = Column(JSON, nullable=False)

    kind = Column(Integer, nullable=False)
    name = Column(String(100), nullable=False)
    theme = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    reusable = Column(Boolean, nullable=False)
    public = Column(Boolean, nullable=False)
    blueprint = Column(Boolean, nullable=False)
    suspended = Column(Boolean, nullable=False, default=False)

    views = Column(Integer, nullable=False, default=0)
    updated = Column(DateTime, nullable=False)

    @classmethod
    def _create(cls, session: Session, json_data: Dict[str, Union[str, int, bool, list]], author: Author):
        json_data["kind"] = PageKind.from_string(json_data["kind"]).value
        entry: cls = cls(**{key: json_data[key] for key in ("id", "kind", "name", "theme", "description",
                                                            "reusable", "public", "blueprint")})
        entry.components = json_dumps(json_data["components"])
        entry.updated = datetime.utcnow()
        entry.author = author
        session.add(entry)
        return entry

    @classmethod
    def find_by_id(cls, session: Session, entry_id: int):
        return first_or_none(session.execute(select(cls).where(cls.id == entry_id)))

    @classmethod
    def create(cls, session: Session, json_data: Dict[str, Union[str, int, bool, list]], author: Author):
        if cls.find_by_id(session, json_data["id"]):
            return None
        return cls._create(session, json_data, author)

    @classmethod
    def create_or_update(cls, session: Session,
                         json_data: Dict[str, Union[str, int, bool, list]],
                         author: Author = None):
        entry: cls
        if (entry := cls.find_by_id(session, json_data["id"])) is None:
            return cls._create(session, json_data, author)
        else:  # redo... maybe...
            session.delete(entry)
            session.commit()
            cls._create(session, json_data, author)

    @classmethod
    def search(cls, session: Session, search: Optional[str], start: int, limit: int) -> list:
        stmt = select(cls)
        # cls.query if search is None else cls.query.whooshee_search(search)
        return session.execute(stmt.offset(start).limit(limit)).scalars().all()  # redo with pagination!!!

    def view(self):  # auto-commit
        self.views += 1

    def delete(self, session: Session):
        session.delete(self)

    def to_json(self):
        return {"id": self.id, "name": self.name, "description": self.description,
                "theme": self.theme, "kind": PageKind(self.kind).name.lower(),
                "components": json_loads(self.components),  # redo?
                "blueprint": self.blueprint, "reusable": self.reusable, "public": self.public,
                "author_id": self.author.id, "author_name": self.author.pseudonym,
                "views": self.views, "updated": self.updated.isoformat()}


class Point(Base):
    __tablename__ = "points"

    module_id = Column(Integer, primary_key=True)
    point_id = Column(Integer, primary_key=True)

    type = Column(Integer, nullable=False)  # 0 - Theory; 1 - HyperBlueprint
    data = Column(PickleType, nullable=False)  # do a relation!

    @classmethod
    def __create(cls, session: Session, module_id: int, point_id: int, point_type: int, data: List[int]):
        if cls.find_by_ids(session, module_id, point_id):
            return False
        new_point = cls(module_id=module_id, point_id=point_id, type=point_type, data=dumps(data))
        session.add(new_point)
        return True

    @classmethod
    def find_by_ids(cls, session: Session, module_id: int, point_id: int):
        return first_or_none(session.execute(select(cls).where(cls.module_id == module_id, cls.point_id == point_id)))

    @classmethod
    def find_and_execute(cls, session: Session, module_id: int, point_id: int) -> int:
        entry: cls = cls.find_by_ids(session, module_id, point_id)
        return entry.execute()

    @classmethod
    def get_module_points(cls, session: Session, module_id: int):
        return session.execute(select(cls).where(cls.module_id == module_id)).scalars().all()

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


class Module(Base, Identifiable):
    @staticmethod
    def create_test_bundle(session: Session):
        if Module.find_by_id(session, 0):
            return
        Module.__create(session, 0, ModuleType.TEST, "Пробник математика ЕГЭ", 4, "math", "une",
                        "enthusiast", 2000, datetime(2020, 10, 22, 10, 30, 3))
        Module.__create(session, 1, ModuleType.THEORY_BLOCK, "История: теория для ЕГЭ", 4, "history", "une",
                        "enthusiast", 1100, datetime(2021, 1, 2, 22, 30, 33))
        Module.__create(session, 2, ModuleType.STANDARD, "Арифметика", 4, "math", "middle-school",
                        "newbie", 100, datetime(2012, 10, 12, 15, 57, 2))
        Module.__create(session, 3, ModuleType.PRACTICE_BLOCK, "100 упражнений по матану", 4, "math", "university",
                        "amateur", 0, datetime(1999, 3, 14, 6, 10, 5))
        Module.__create(session, 4, ModuleType.STANDARD, "English ABCs", 4, "languages", "hobby",
                        "review", 2000, datetime(2019, 7, 22, 22, 10, 45))
        Module.__create(session, 5, ModuleType.STANDARD, "Веб Дизайн", 4, "informatics", "prof-skills",
                        "enthusiast", 2000, datetime(2020, 10, 22, 10, 30, 8))
        Module.__create(session, 6, ModuleType.STANDARD, "Робототехника", 4, "informatics", "clubs",
                        "newbie", 3100, datetime(2021, 1, 2, 22, 30, 33))
        Module.__create(session, 7, ModuleType.TEST, "Архитектура XIX века", 4, "arts", "university",
                        "expert", 5, datetime(2012, 6, 12, 15, 57, 0))
        Module.__create(session, 8, ModuleType.STANDARD, "Безопасность в интернете", 4, "informatics", "university",
                        "review", 2002, datetime(1999, 3, 14, 6, 10, 5))
        Module.__create(session, 9, ModuleType.THEORY_BLOCK, "Литература", 4, "literature", "bne",
                        "enthusiast", 300, datetime(2019, 7, 12, 22, 10, 40))
        Module.__create(session, 10, ModuleType.THEORY_BLOCK, "Классическая Музыка", 4, "arts", "hobby",
                        "enthusiast", 2000, datetime(2019, 3, 22, 22, 10, 40))
        Module.__create(session, 11, ModuleType.STANDARD, "Немецкий язык", 4, "languages", "main-school",
                        "enthusiast", 700, datetime(2015, 7, 22, 22, 10, 40))
        Module.__create(session, 12, ModuleType.PRACTICE_BLOCK, "География: контурные карты", 4, "geography", "hobby",
                        "review", 2000, datetime(2019, 7, 22, 22, 1, 40))
        Module.__create(session, 13, ModuleType.STANDARD, "Геодезия", 4, "geography", "hobby",
                        "review", 2000, datetime(2016, 7, 22, 2, 52, 40))
        Module.__create(session, 14, ModuleType.STANDARD, "Океанология", 4, "geography", "hobby",
                        "review", 2000, datetime(2019, 7, 22, 22, 46, 40))
        Module.__create(session, 15, ModuleType.TEST, "Ораторское искусство", 4, "arts", "prof-skills",
                        "amateur", 1200, datetime(2009, 7, 22, 22, 31, 0))
        Module.__create(session, 16, ModuleType.THEORY_BLOCK, "Социология", 4, "social-science", "university",
                        "review", 2000, datetime(2012, 6, 12, 15, 57, 0))
        Module.__create(session, 17, ModuleType.STANDARD, "Классическая философия", 4, "philosophy", "hobby",
                        "review", 700, datetime(2019, 7, 22, 22, 11, 40))
        Module.__create(session, 18, ModuleType.STANDARD, "Физика: термодинамика", 4, "physics", "main-school",
                        "review", 4200, datetime(2012, 7, 22, 2, 10, 54))
        Module.__create(session, 19, ModuleType.PRACTICE_BLOCK, "История России", 4, "history", "hobby",
                        "review", 270, datetime(2019, 7, 22, 22, 10, 24))
        Module.__create(session, 20, ModuleType.STANDARD, "Информатика 7 класс", 4, "informatics", "middle-school",
                        "amateur", 2000, datetime(2019, 7, 22, 22, 10, 12))
        Module.__create(session, 21, ModuleType.TEST, "Литература Европы XX века", 4, "literature", "hobby",
                        "review", 2000, datetime(2019, 5, 13, 1, 1, 54))
        Module.__create(session, 22, ModuleType.PRACTICE_BLOCK, "Python", 4, "informatics", "clubs",
                        "newbie", 1500, datetime(2019, 7, 22, 22, 10, 32))

    __tablename__ = "modules"
    not_found_text = "Module not found"

    # Essentials
    id = Column(Integer, primary_key=True)
    length = Column(Integer, nullable=False)  # the amount of schedule or map points
    type = Column(Integer, nullable=False)  # 0 - standard; 1 - practice; 2 - theory; 3 - test
    name = Column(String(100), nullable=False)  # the name for the diagram (course map)

    # Filtering:
    theme = Column(String(20), nullable=False)
    category = Column(String(20), nullable=False)
    difficulty = Column(String(20), nullable=False)

    # Sorting:
    popularity = Column(Integer, nullable=False, default=1000)
    creation_date = Column(DateTime, nullable=False)

    # Author-related
    author = Column(Integer, ForeignKey("authors.id"), nullable=False,
                    default=0)

    @classmethod
    def __create(cls, session: Session, module_id: int, module_type: ModuleType, name: str, length: int, theme: str,
                 category: str, difficulty: str, popularity: int, creation_date: datetime = None):
        if creation_date is None:
            creation_date = datetime.utcnow()
        new_module = cls(id=module_id, type=module_type.value, name=name, length=length,
                         theme=theme, category=category, difficulty=difficulty,
                         popularity=popularity, creation_date=creation_date)
        session.add(new_module)
        return True

    @classmethod
    def find_by_id(cls, session: Session, module_id: int):
        return first_or_none(session.execute(select(cls).where(cls.id == module_id)))

    @classmethod
    def get_module_list(cls, session: Session, filters: Optional[Dict[str, str]],
                        user_id: int, offset: int, limit: int) -> list:
        query: BaseQuery = cls.query
        # explore joining queries!
        query = query.filter(cls.id.notin_(ModuleFilterSession.filter_ids_by_user(session, user_id, hidden=True)))

        if filters is not None:
            keys: List[str] = list(filters.keys())
            if "global" in keys:
                global_filter: str = filters["global"]
                if global_filter == "pinned":
                    # joining queries!
                    query = query.filter(cls.id.in_(ModuleFilterSession.filter_ids_by_user(session, user_id, pinned=True)))
                elif global_filter == "starred":
                    query = query.filter(cls.id.in_(ModuleFilterSession.filter_ids_by_user(session, user_id, starred=True)))
                elif global_filter == "started":
                    query = query.filter(cls.id.in_(ModuleFilterSession.filter_ids_by_user(session, user_id, started=True)))

            if "difficulty" in keys:
                query = query.filter_by(difficulty=filters["difficulty"])
            if "category" in keys:
                query = query.filter_by(category=filters["category"])
            if "theme" in keys:
                query = query.filter_by(theme=filters["theme"])

        return query.offset(offset).limit(limit).all()

    def get_any_point(self, session: Session) -> Point:
        return Point.find_by_ids(session, self.id, randint(1, self.length))

    def to_short_json(self) -> dict:
        return {"id": self.id, "name": self.name, "author": self.author}

    def to_json(self, session: Session, user_id: int = None) -> dict:
        result: dict = self.to_short_json()
        if user_id is not None:
            result.update(ModuleFilterSession.find_json(session, user_id, self.id))
        result.update({"theme": self.theme, "difficulty": self.difficulty, "category": self.category,
                       "type": ModuleType(self.type).name.lower().replace("_", "-")})
        return result
