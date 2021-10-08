from datetime import datetime
from json import dumps as json_dumps, load
from pickle import dumps, loads
from random import randint
from typing import Dict, List, Optional, Union

from sqlalchemy import Column, ForeignKey, select, and_, or_
from sqlalchemy.orm import relationship
from sqlalchemy.sql import Select
from sqlalchemy.sql.sqltypes import Integer, String, Boolean, JSON, DateTime, PickleType, Text
from sqlalchemy_enum34 import EnumType

from authorship import Author
from componets import Identifiable, TypeEnum, create_marshal_model, Marshalable, LambdaFiledDef
from componets.checkers import first_or_none, register_as_searchable
from education.sessions import ModuleFilterSession as MFS
from main import Base, Session  # , whooshee


class PageKind(TypeEnum):
    THEORY = 0
    PRACTICE = 1
    TASK = 2


# @whooshee.register_model("name", "theme", "description")
@register_as_searchable("name", "theme", "description")
@create_marshal_model("main", "id", "name", "description", "theme", "kind", "components")
@create_marshal_model("short", "author", "blueprint", "components", "public", "reusable", "suspended", full=True)
class Page(Base, Identifiable, Marshalable):
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
    author = relationship("Author", foreign_keys=[author_id])
    components = Column(JSON, nullable=False)

    kind = Column(EnumType(PageKind, by_name=True), nullable=False)
    name = Column(Text, nullable=False)
    theme = Column(Text, nullable=False)
    description = Column(Text, nullable=True)

    reusable = Column(Boolean, nullable=False)
    public = Column(Boolean, nullable=False)
    blueprint = Column(Boolean, nullable=False)
    suspended = Column(Boolean, nullable=False, default=False)

    views = Column(Integer, nullable=False, default=0)
    updated = Column(DateTime, nullable=False)

    author_name: LambdaFiledDef = LambdaFiledDef("short", "author_name", str, lambda page: page.author.pseudonym)

    @classmethod
    def _create(cls, session: Session, json_data: Dict[str, Union[str, int, bool, list]], author: Author):
        json_data["kind"] = PageKind.from_string(json_data["kind"])
        entry: cls = cls(**{key: json_data[key] for key in ("id", "kind", "name", "theme", "description",
                                                            "reusable", "public", "blueprint")})
        entry.components = json_dumps(json_data["components"], ensure_ascii=False)
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
    def get_page_of_pages(cls, session: Session, start: int, limit: int) -> list:
        return session.execute(select(cls).offset(start).limit(limit)).scalars().all()

    @classmethod
    def search(cls, session: Session, search: Optional[str], start: int, limit: int) -> list:
        if search is None or len(search) < 3:  # redo all search with pagination!!!
            return cls.get_page_of_pages(session, start, limit)
        return session.execute(cls.search_stmt(search).offset(start).limit(limit)).scalars().all()

    def view(self):  # auto-commit
        self.views += 1

    def delete(self, session: Session):
        session.delete(self)


class PointType(TypeEnum):
    THEORY = 0
    PRACTICE = 1


class Point(Base):
    __tablename__ = "points"

    module_id = Column(Integer, primary_key=True)
    point_id = Column(Integer, primary_key=True)

    type = Column(EnumType(PointType, by_name=True), nullable=False)
    data = Column(PickleType, nullable=False)  # do a relation!

    @classmethod
    def __create(cls, session: Session, module_id: int, point_id: int, point_type: int, data: List[int]):
        if cls.find_by_ids(session, module_id, point_id):
            return False
        new_point = cls(module_id=module_id, point_id=point_id, type=point_type, data=dumps(data))
        session.add(new_point)
        return True

    @classmethod
    def create_all(cls, session: Session, module_id: int, json_data: List[Dict[str, Union[str, int, list]]]):
        for i in range(len(json_data)):
            cls.__create(session, module_id, i, PointType.from_string(json_data[i]["type"]), json_data[i]["pages"])

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

    def delete(self, session: Session):
        session.delete(self)


class ModuleType(TypeEnum):
    STANDARD = 0
    PRACTICE_BLOCK = 1
    THEORY_BLOCK = 2
    TEST = 3


class SortType(str, TypeEnum):
    POPULARITY = "popularity"
    VISIT_DATE = "visit-date"
    CREATION_DATE = "creation-date"


@register_as_searchable("name", "description")
class Module(Base, Identifiable):
    @staticmethod
    def create_test_bundle(session: Session, author: Author):
        if Module.find_by_id(session, 0):
            return
        Module.__create(session, 0, ModuleType.TEST, "Пробник математика ЕГЭ", 4, "math", "une",
                        "enthusiast", 2000, author, datetime(2020, 10, 22, 10, 30, 3))
        Module.__create(session, 1, ModuleType.THEORY_BLOCK, "История: теория для ЕГЭ", 4, "history", "une",
                        "enthusiast", 1100, author, datetime(2021, 1, 2, 22, 30, 33))
        Module.__create(session, 2, ModuleType.STANDARD, "Арифметика", 4, "math", "middle-school",
                        "newbie", 100, author, datetime(2012, 10, 12, 15, 57, 2))
        Module.__create(session, 3, ModuleType.PRACTICE_BLOCK, "100 упражнений по матану", 4, "math", "university",
                        "amateur", 0, author, datetime(1999, 3, 14, 6, 10, 5))
        Module.__create(session, 4, ModuleType.STANDARD, "English ABCs", 4, "languages", "hobby",
                        "review", 2000, author, datetime(2019, 7, 22, 22, 10, 45))
        Module.__create(session, 5, ModuleType.STANDARD, "Веб Дизайн", 4, "informatics", "prof-skills",
                        "enthusiast", 2000, author, datetime(2020, 10, 22, 10, 30, 8))
        Module.__create(session, 6, ModuleType.STANDARD, "Робототехника", 4, "informatics", "clubs",
                        "newbie", 3100, author, datetime(2021, 1, 2, 22, 30, 33))
        Module.__create(session, 7, ModuleType.TEST, "Архитектура XIX века", 4, "arts", "university",
                        "expert", 5, author, datetime(2012, 6, 12, 15, 57, 0))
        Module.__create(session, 8, ModuleType.STANDARD, "Безопасность в интернете", 4, "informatics", "university",
                        "review", 2002, author, datetime(1999, 3, 14, 6, 10, 5))
        Module.__create(session, 9, ModuleType.THEORY_BLOCK, "Литература", 4, "literature", "bne",
                        "enthusiast", 300, author, datetime(2019, 7, 12, 22, 10, 40))
        Module.__create(session, 10, ModuleType.THEORY_BLOCK, "Классическая Музыка", 4, "arts", "hobby",
                        "enthusiast", 2000, author, datetime(2019, 3, 22, 22, 10, 40))
        Module.__create(session, 11, ModuleType.STANDARD, "Немецкий язык", 4, "languages", "main-school",
                        "enthusiast", 700, author, datetime(2015, 7, 22, 22, 10, 40))
        Module.__create(session, 12, ModuleType.PRACTICE_BLOCK, "География: контурные карты", 4, "geography", "hobby",
                        "review", 2000, author, datetime(2019, 7, 22, 22, 1, 40))
        Module.__create(session, 13, ModuleType.STANDARD, "Геодезия", 4, "geography", "hobby",
                        "review", 2000, author, datetime(2016, 7, 22, 2, 52, 40))
        Module.__create(session, 14, ModuleType.STANDARD, "Океанология", 4, "geography", "hobby",
                        "review", 2000, author, datetime(2019, 7, 22, 22, 46, 40))
        Module.__create(session, 15, ModuleType.TEST, "Ораторское искусство", 4, "arts", "prof-skills",
                        "amateur", 1200, author, datetime(2009, 7, 22, 22, 31, 0))
        Module.__create(session, 16, ModuleType.THEORY_BLOCK, "Социология", 4, "social-science", "university",
                        "review", 2000, author, datetime(2012, 6, 12, 15, 57, 0))
        Module.__create(session, 17, ModuleType.STANDARD, "Классическая философия", 4, "philosophy", "hobby",
                        "review", 700, author, datetime(2019, 7, 22, 22, 11, 40))
        Module.__create(session, 18, ModuleType.STANDARD, "Физика: термодинамика", 4, "physics", "main-school",
                        "review", 4200, author, datetime(2012, 7, 22, 2, 10, 54))
        Module.__create(session, 19, ModuleType.PRACTICE_BLOCK, "История России", 4, "history", "hobby",
                        "review", 270, author, datetime(2019, 7, 22, 22, 10, 24))
        Module.__create(session, 20, ModuleType.STANDARD, "Информатика 7 класс", 4, "informatics", "middle-school",
                        "amateur", 2000, author, datetime(2019, 7, 22, 22, 10, 12))
        Module.__create(session, 21, ModuleType.TEST, "Литература Европы XX века", 4, "literature", "hobby",
                        "review", 2000, author, datetime(2019, 5, 13, 1, 1, 54))
        Module.__create(session, 22, ModuleType.PRACTICE_BLOCK, "Python", 4, "informatics", "clubs",
                        "newbie", 1500, author, datetime(2019, 7, 22, 22, 10, 32))

    __tablename__ = "modules"
    not_found_text = "Module not found"

    # Essentials
    id = Column(Integer, primary_key=True)
    length = Column(Integer, nullable=False)  # the amount of schedule or map points
    type = Column(EnumType(ModuleType, by_name=True), nullable=False)

    # Searchable:
    name = Column(Text, nullable=False)
    description = Column(Text, nullable=True)

    # Filtering:
    theme = Column(String(20), nullable=False)
    category = Column(String(20), nullable=False)
    difficulty = Column(String(20), nullable=False)

    # Metrics & Sorting:
    views = Column(Integer, nullable=False, default=0)
    popularity = Column(Integer, nullable=False, default=1000)
    created = Column(DateTime, nullable=False)

    # Author-related
    author_id = Column(Integer, ForeignKey("authors.id"), nullable=False)
    author = relationship("Author")  # redo all modules for it

    image_id = Column(Integer, nullable=True)

    @classmethod
    def __create(cls, session: Session, module_id: int, module_type: ModuleType, name: str, length: int, theme: str,
                 category: str, difficulty: str, popularity: int, author: Author, creation_date: datetime = None):
        if creation_date is None:
            creation_date = datetime.utcnow()
        new_module = cls(id=module_id, type=module_type, name=name, length=length,
                         theme=theme, category=category, difficulty=difficulty,
                         popularity=popularity, created=creation_date)
        new_module.author = author
        session.add(new_module)
        return True

    @classmethod
    def _create(cls, session: Session, json_data: Dict[str, Union[str, int, bool, list]], author: Author):
        json_data["type"] = ModuleType.from_string(json_data["type"])
        json_data["length"] = len(json_data["points"])

        entry: cls = cls(**{key: json_data[key] for key in ("id", "length", "type", "name", "description",
                                                            "theme", "category", "difficulty")})
        if "image-id" in json_data.keys():
            entry.image_id = json_data["image-id"]
        entry.created = datetime.utcnow()
        entry.author = author

        session.add(entry)
        session.flush()

        Point.create_all(session, entry.id, json_data["points"])

        return entry

    @classmethod
    def find_by_id(cls, session: Session, module_id: int):
        return first_or_none(session.execute(select(cls).where(cls.id == module_id)))

    @classmethod
    def create(cls, session: Session, json_data: Dict[str, Union[str, int, bool, list]], author: Author):
        if cls.find_by_id(session, json_data["id"]):
            return None
        return cls._create(session, json_data, author)

    @classmethod
    def get_module_list(cls, session: Session, filters: Optional[Dict[str, str]], search: str,
                        sort: SortType, user_id: int, offset: int, limit: int) -> list:

        # print(filters, search, sort)
        # print([(mfs.module_id, mfs.user_id, mfs.to_json()) for mfs in session.execute(select(MFS)).scalars().all()])

        stmt: Select = select(cls) if search is None or len(search) < 3 else cls.search_stmt(search)

        global_filter: Optional[str] = None
        if filters is not None:
            if "global" in filters.keys():
                global_filter = filters.pop("global")
            stmt = stmt.filter_by(**filters)

        # print(len(session.execute(stmt).scalars().all()))

        stmt = stmt.outerjoin(MFS, and_(MFS.module_id == cls.id, MFS.user_id == user_id))
        # if session exists for another user, would it pick it up???

        # print(len(session.execute(stmt).scalars().all()))

        stmt = stmt.filter(or_(MFS.hidden != True, MFS.hidden.is_(None)))

        # print(len(session.execute(stmt).scalars().all()))

        if global_filter is not None:
            stmt = stmt.filter_by(**{global_filter: True})

        if sort == SortType.POPULARITY:  # reverse?
            stmt = stmt.order_by(cls.views)
        elif sort == SortType.CREATION_DATE:
            stmt = stmt.order_by(cls.created.desc())
        elif sort == SortType.VISIT_DATE:
            stmt = stmt.order_by(MFS.last_visited.desc())

        # print(len(session.execute(stmt.offset(offset).limit(limit)).scalars().all()))
        # print(stmt)

        return session.execute(stmt.offset(offset).limit(limit)).scalars().all()

    @classmethod
    def get_hidden_module_list(cls, session: Session, user_id: int, offset: int, limit: int):
        stmt: Select = select(cls).join(MFS, and_(MFS.module_id == cls.id, MFS.user_id == user_id, MFS.hidden == True))
        stmt = stmt.order_by(MFS.last_changed.desc())
        # print(*[(mfs.module_id, mfs.user_id, mfs.last_changed.isoformat())
        #         for mfs in session.execute(select(MFS)).scalars().all() if mfs.hidden], sep="\n")
        # print(stmt)
        return session.execute(stmt.offset(offset).limit(limit)).scalars().all()

    def get_any_point(self, session: Session) -> Point:
        return Point.find_by_ids(session, self.id, randint(1, self.length))

    def to_short_json(self) -> dict:
        return {"id": self.id, "name": self.name, "author-id": self.author_id, "image-id": self.image_id}

    def to_json(self, session: Session, user_id: int = None) -> dict:
        result: dict = self.to_short_json()
        if user_id is not None:
            result.update(MFS.find_json(session, user_id, self.id))
        result.update({"theme": self.theme, "difficulty": self.difficulty, "category": self.category,
                       "type": self.type.to_string(), "description": self.description,
                       "views": self.views, "created": self.created.isoformat()})
        return result

    def delete(self, session: Session):
        for point in Point.get_module_points(session, self.id):
            point.delete(session)
        session.delete(self)
