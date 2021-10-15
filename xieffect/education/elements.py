from __future__ import annotations

from datetime import datetime
from json import dumps as json_dumps, load
from random import randint
from typing import Dict, List, Optional, Union, Any

from sqlalchemy import Column, ForeignKey, ForeignKeyConstraint, select, and_, or_
from sqlalchemy.engine import Row
from sqlalchemy.orm import relationship
from sqlalchemy.sql import Select
from sqlalchemy.sql.sqltypes import Integer, String, Boolean, JSON, DateTime, Text
from sqlalchemy_enum34 import EnumType

from authorship import Author
from componets import Identifiable, TypeEnum, create_marshal_model, Marshalable, LambdaFieldDef
from componets.checkers import first_or_none, register_as_searchable
from education.sessions import ModuleFilterSession as MFS
from main import Base, Session  # , whooshee


class PageKind(TypeEnum):
    THEORY = 0
    PRACTICE = 1
    TASK = 2


# @whooshee.register_model("name", "theme", "description")
@register_as_searchable("name", "theme", "description")
@create_marshal_model("page-main", "components", inherit="page-base")
@create_marshal_model("page-short", "author_id", "views", "updated", inherit="page-base")
@create_marshal_model("page-base", "id", "name", "kind", "theme", "description")
class Page(Base, Identifiable, Marshalable):
    @staticmethod
    def create_test_bundle(session: Session, author: Author):
        for i in range(1, 4):
            with open(f"../files/tfs/test/{i}.json", "rb") as f:
                Page.create(session, load(f), author)

    __tablename__ = "pages"
    not_found_text = "Page not found"
    directory = "files/tfs/cat-pages/"

    id = Column(Integer, ForeignKey("wip-pages.id"), primary_key=True)
    author_id = Column(Integer, ForeignKey("authors.id"), nullable=False)
    author = relationship("Author")
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

    author_name: LambdaFieldDef = LambdaFieldDef("page-short", str, lambda page: page.author.pseudonym)

    @classmethod
    def _create(cls, session: Session, json_data: Dict[str, Union[str, int, bool, list]], author: Author) -> Page:
        json_data["kind"] = PageKind.from_string(json_data["kind"])
        entry: cls = cls(**{key: json_data[key] for key in ("id", "kind", "name", "theme", "description",
                                                            "reusable", "public", "blueprint")})
        entry.components = json_dumps(json_data["components"], ensure_ascii=False)
        entry.updated = datetime.utcnow()
        entry.author = author
        session.add(entry)
        return entry

    @classmethod
    def find_by_id(cls, session: Session, entry_id: int) -> Optional[Page]:
        return first_or_none(session.execute(select(cls).where(cls.id == entry_id)))

    @classmethod
    def create(cls, session: Session, json_data: Dict[str, Any], author: Author) -> Optional[Page]:
        if cls.find_by_id(session, json_data["id"]):
            return None
        return cls._create(session, json_data, author)

    @classmethod
    def create_or_update(cls, session: Session, json_data: Dict[str, Any], author: Author = None) -> Page:
        entry: cls
        if (entry := cls.find_by_id(session, json_data["id"])) is None:
            return cls._create(session, json_data, author)
        else:  # redo... maybe...
            session.delete(entry)
            session.commit()
            cls._create(session, json_data, author)

    @classmethod
    def search(cls, session: Session, search: Optional[str], start: int, limit: int) -> list[Page]:
        stmt: Select = select(cls).filter_by(public=True).offset(start).limit(limit)
        if search is not None and len(search) > 2:  # redo all search with pagination!!!
            stmt = cls.search_stmt(search, stmt=stmt)
        return session.execute(stmt).scalars().all()

    def view(self) -> None:  # auto-commit
        self.views += 1

    def delete(self, session: Session) -> None:
        session.delete(self)


class PointToPage(Base):
    __tablename__ = "points_to_pages"

    __table_args__ = (ForeignKeyConstraint(("module_id", "point_id"), ("points.module_id", "points.point_id")),)

    module_id = Column(Integer, primary_key=True)
    point_id = Column(Integer, primary_key=True)
    position = Column(Integer, primary_key=True)

    page_id = Column(Integer, ForeignKey("pages.id"), primary_key=True)
    page = relationship("Page")


class PointType(TypeEnum):
    THEORY = 0
    PRACTICE = 1


class Point(Base):
    __tablename__ = "points"

    module = relationship("Module", back_populates="points")
    module_id = Column(Integer, ForeignKey("modules.id"), primary_key=True)
    point_id = Column(Integer, primary_key=True)

    type = Column(EnumType(PointType, by_name=True), nullable=False)
    length = Column(Integer, nullable=False)

    pages = relationship("PointToPage", order_by=PointToPage.position)

    @classmethod
    def create(cls, session, module_id: int, point_id: int, point_data: Dict[str, str]) -> Point:
        point = cls(
            module_id=module_id, point_id=point_id, length=len(point_data["pages"]),
            type=PointType.from_string(point_data["type"])
        )
        point.pages.extend([
            PointToPage(position=i, page_id=page_id)
            for i, page_id in enumerate(point_data["pages"])
        ])
        session.add(point)
        return point


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
@create_marshal_model("module-meta", "map", "timer", inherit="module-index")
@create_marshal_model("module-index", "theme", "difficulty", "category", "type",
                      "description", "views", "created", inherit="module-short")
@create_marshal_model("module-short", "id", "name", "author_id", "image_id")
class Module(Base, Identifiable, Marshalable):
    __tablename__ = "modules"
    not_found_text = "Module not found"

    # Essentials:
    id = Column(Integer, ForeignKey("wip-modules.id"), primary_key=True)
    length = Column(Integer, nullable=False)  # the amount of schedule or map points
    type = Column(EnumType(ModuleType, by_name=True), nullable=False)

    # Type-dependent:
    map = Column(JSON, nullable=True)
    timer = Column(Integer, nullable=True)

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
    author = relationship("Author", back_populates="modules")  # redo all modules for it
    author_name: LambdaFieldDef = LambdaFieldDef("module-short", str, lambda module: module.pseudonym)

    # Other relations or relation-like
    image_id = Column(Integer, nullable=True)
    points = relationship("Point", back_populates="module", cascade="all, delete", order_by=Point.point_id)

    @classmethod
    def create(cls, session: Session, json_data: Dict[str, Any], author: Author, force: bool = False) -> Module:
        if cls.find_by_id(session, json_data["id"]):
            return

        json_data["type"] = ModuleType.from_string(json_data["type"])
        json_data["length"] = len(json_data["points"])

        entry: cls = cls(**{key: json_data[key] for key in ("id", "length", "type", "name", "description",
                                                            "theme", "category", "difficulty")})
        entry.image_id = json_data.get("image-id", None)
        if "map" in json_data.keys():
            entry.map = json_dumps(json_data["map"], ensure_ascii=False)

        if force:
            entry.views = json_data.get("views", 0)
        if force and "created" in json_data.keys():
            entry.created = datetime.fromisoformat(json_data["created"])
        else:
            entry.created = datetime.utcnow()

        entry.author = author
        entry.points.extend([
            Point.create(session, entry.id, point_id, point_data)
            for point_id, point_data in enumerate(json_data["points"])
        ])

        session.add(entry)
        session.flush()

        return entry

    @classmethod
    def find_by_id(cls, session: Session, module_id: int) -> Optional[Module]:
        return first_or_none(session.execute(select(cls).where(cls.id == module_id)))

    @classmethod
    def create(cls, session: Session, json_data: Dict[str, Any], author: Author) -> Optional[Module]:
        if cls.find_by_id(session, json_data["id"]):
            return None
        return cls.create(session, json_data, author)

    @classmethod
    def find_with_relation(cls, session: Session, module_id: int, user_id: int) -> Optional[Row]:
        stmt: Select = select(*cls.__table__.columns, *MFS.__table__.columns, Author.pseudonym)
        stmt = stmt.outerjoin(MFS, and_(MFS.module_id == cls.id, MFS.user_id == user_id))
        result = session.execute(stmt.filter(cls.id == module_id).limit(1)).all()
        return result[0] if len(result) else None

    @classmethod
    def get_module_list(cls, session: Session, filters: Optional[Dict[str, str]], search: str,
                        sort: SortType, user_id: int, offset: int, limit: int) -> List[Row]:

        # print(filters, search, sort)
        # print([(mfs.module_id, mfs.user_id, mfs.to_json()) for mfs in session.execute(select(MFS)).scalars().all()])

        stmt: Select = select(*cls.__table__.columns, *MFS.__table__.columns, Author.pseudonym)

        # print(len(session.execute(stmt).all()), stmt)

        if search is not None and len(search) > 2:
            stmt = cls.search_stmt(search, stmt=stmt)

        # print(len(session.execute(stmt).scalars().all()), stmt)

        global_filter: Optional[str] = None
        if filters is not None:
            if "global" in filters.keys():
                global_filter = filters.pop("global")
            stmt = stmt.filter_by(**filters)

        # print(len(session.execute(stmt).scalars().all()), stmt)

        stmt = stmt.outerjoin(MFS, and_(MFS.module_id == cls.id, MFS.user_id == user_id))
        # if session exists for another user, would it pick it up???

        # print(len(session.execute(stmt).all()))

        stmt = stmt.filter(or_(MFS.hidden != True, MFS.hidden.is_(None)))

        # print(len(session.execute(stmt).scalars().all()), stmt)

        if global_filter is not None:
            stmt = stmt.filter_by(**{global_filter: True})

        if sort == SortType.POPULARITY:  # reverse?
            stmt = stmt.order_by(cls.views)
        elif sort == SortType.CREATION_DATE:
            stmt = stmt.order_by(cls.created.desc())
        elif sort == SortType.VISIT_DATE:
            stmt = stmt.order_by(MFS.last_visited.desc())

        # print(len(session.execute(stmt.offset(offset).limit(limit)).scalars().all()), stmt)
        # print(stmt)
        # print(session.execute(stmt.offset(offset).limit(limit)).first())

        return session.execute(stmt.offset(offset).limit(limit)).all()

    @classmethod
    def get_hidden_module_list(cls, session: Session, user_id: int, offset: int, limit: int) -> list[Row]:
        stmt: Select = select(*cls.__table__.columns, Author.pseudonym)
        stmt = stmt.join(MFS, and_(MFS.module_id == cls.id, MFS.user_id == user_id, MFS.hidden == True))
        stmt = stmt.order_by(MFS.last_changed.desc())
        # print(*[(mfs.module_id, mfs.user_id, mfs.last_changed.isoformat())
        #         for mfs in session.execute(select(MFS)).scalars().all() if mfs.hidden], sep="\n")
        # print(stmt)
        return session.execute(stmt.offset(offset).limit(limit)).all()

    def execute_point(self, point_id: int = None, theory_level: float = None):
        if point_id is None:
            point_id = randint(1, self.length)

        point: Point = self.points[point_id]
        if point is None:
            return None

        page_position: int
        if point.type == PointType.PRACTICE:
            page_position = randint(0, point.length - 1)
        elif theory_level is None:
            page_position = 0
        elif theory_level < 1:
            page_position = int(theory_level * point.length)
        else:
            page_position = point.length - 1

        return point.pages[page_position].page_id

    def delete(self, session: Session) -> None:
        session.delete(self)
