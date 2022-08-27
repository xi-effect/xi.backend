from __future__ import annotations

from datetime import datetime
from random import randint
from typing import Union

from sqlalchemy import Column, ForeignKey, ForeignKeyConstraint, select, and_, or_
from sqlalchemy.engine import Row
from sqlalchemy.orm import relationship
from sqlalchemy.sql import Select
from sqlalchemy.sql.sqltypes import Integer, String, Boolean, JSON, DateTime, Text, Enum

from common import Identifiable, TypeEnum, create_marshal_model, Marshalable, PydanticModel
from common import LambdaFieldDef, index_service, Base, sessionmaker
from ._base_session import BaseModuleSession
from ..authorship.user_roles_db import Author


class PreferenceOperation(TypeEnum):
    HIDE = 0
    SHOW = 1
    STAR = 2
    UNSTAR = 3
    PIN = 4
    UNPIN = 5


@create_marshal_model("mfs-full", "started", "starred", "pinned", use_defaults=True)  # TODO replace with new-marshals
class ModuleFilterSession(BaseModuleSession, Marshalable):
    __tablename__ = "module-filter-sessions"
    not_found_text = "Session not found"

    started = Column(Boolean, nullable=False, default=False)
    starred = Column(Boolean, nullable=False, default=False)
    pinned = Column(Boolean, nullable=False, default=False)
    hidden = Column(Boolean, nullable=False, default=False)

    last_visited = Column(DateTime, nullable=True)  # None for not visited
    last_changed = Column(DateTime, nullable=True)

    @PydanticModel.include_columns(started, starred, pinned)
    class IndexModel(BaseModuleSession.BaseModel):
        pass

    @classmethod
    def create(cls, session: sessionmaker, user_id: int, module_id: int) -> Union[ModuleFilterSession, None]:
        if cls.find_by_ids(session, user_id, module_id) is not None:
            return None
        return super().create(session, user_id=user_id, module_id=module_id, last_changed=datetime.utcnow())

    def note_change(self) -> None:  # auto-commit
        self.last_changed = datetime.utcnow()

    def visit_now(self) -> None:  # auto-commit
        self.last_visited = datetime.utcnow()
        self.note_change()

    def change_preference(self, session: sessionmaker, operation: PreferenceOperation) -> None:
        if operation == PreferenceOperation.HIDE:
            self.hidden = True
        elif operation == PreferenceOperation.SHOW:
            self.hidden = False
        elif operation == PreferenceOperation.STAR:
            self.starred = True
        elif operation == PreferenceOperation.UNSTAR:
            self.starred = False
        elif operation == PreferenceOperation.PIN:
            self.pinned = True
        elif operation == PreferenceOperation.UNPIN:
            self.pinned = False
        if not any((self.hidden, self.pinned, self.starred, self.started)):
            self.delete(session)
        else:
            self.note_change()


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

    type = Column(Enum(PointType), nullable=False)
    length = Column(Integer, nullable=False)

    pages = relationship("PointToPage", cascade="all, delete", order_by=PointToPage.position)

    @classmethod
    def create(cls, session, module_id: int, point_id: int, point_data: dict[str, str]) -> Point:
        point = cls(
            module_id=module_id, point_id=point_id, length=len(point_data["pages"]),
            type=PointType.from_string(point_data["type"])
        )
        point.pages.extend([
            PointToPage(position=i, page_id=page_id)
            for i, page_id in enumerate(point_data["pages"])
        ])
        session.add(point)
        session.flush()
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


@index_service.register_as_searchable("name", "description")
@create_marshal_model("module-meta", "map", "timer", inherit="module-index")  # TODO replace with new-marshals
@create_marshal_model("module-index", "theme", "difficulty", "category", "type",  # TODO replace with new-marshals
                      "description", "views", "created", "id", "name", "author_id", "image_id")
class Module(Base, Identifiable, Marshalable):  # TODO update with new-mars
    __tablename__ = "modules"
    not_found_text = "Module not found"

    # Essentials:
    id = Column(Integer, ForeignKey("wip-modules.id"), primary_key=True)
    length = Column(Integer, nullable=False)  # the amount of schedule or map points
    type = Column(Enum(ModuleType), nullable=False)

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

    ShortModel = PydanticModel.column_model(id, name, author_id, image_id)

    @classmethod
    def create(cls, session: sessionmaker, json_data: dict[str, ...], author: Author,
               force: bool = False) -> Union[Module, None]:
        if cls.find_by_id(session, json_data["id"]):
            return

        json_data["type"] = ModuleType.from_string(json_data["type"])
        json_data["length"] = len(json_data["points"])

        entry: cls = cls(**{key: json_data[key] for key in ("id", "length", "type", "name", "description",
                                                            "theme", "category", "difficulty")})
        entry.image_id = json_data.get("image-id", None)
        if "map" in json_data.keys():
            entry.map = json_data["map"]

        if force:
            entry.views = json_data.get("views", 0)
        if force and "created" in json_data.keys():
            entry.created = datetime.fromisoformat(json_data["created"])
        else:
            entry.created = datetime.utcnow()

        entry.author = author
        # noinspection PyTypeChecker
        entry.points.extend([
            Point.create(session, entry.id, point_id, point_data)
            for point_id, point_data in enumerate(json_data["points"])
        ])

        session.add(entry)
        session.flush()

        return entry

    @classmethod
    def find_by_id(cls, session: sessionmaker, module_id: int) -> Union[Module, None]:
        return cls.find_first_by_kwargs(session, id=module_id)

    @classmethod
    def find_or_create(cls, session: sessionmaker, json_data: dict[str, ...], author: Author) -> Union[Module, None]:
        if cls.find_by_id(session, json_data["id"]):
            return None
        return cls.create(session, json_data, author)

    @classmethod
    def find_with_relation(cls, session: sessionmaker, module_id: int, user_id: int) -> Union[Row, None]:
        stmt: Select = select(*cls.__table__.columns, *ModuleFilterSession.__table__.columns, Author.pseudonym)
        stmt = stmt.outerjoin(ModuleFilterSession, and_(ModuleFilterSession.module_id == cls.id,
                                                        ModuleFilterSession.user_id == user_id))
        return session.get_first_row(stmt.filter(cls.id == module_id).limit(1))

    @classmethod
    def get_module_list(cls, session: sessionmaker, filters: Union[dict[str, str], None], search: str,
                        sort: SortType, user_id: int, offset: int, limit: int) -> list[Row]:

        # print(filters, search, sort)
        # print([(mfs.module_id, mfs.user_id, mfs.to_json())
        # for mfs in session.execute(select(ModuleFilterSession)).scalars().all()])

        stmt = select(*cls.__table__.columns, *ModuleFilterSession.__table__.columns, Author.pseudonym)

        # print(len(session.execute(stmt).all()), stmt)

        if search is not None and len(search) > 2:
            stmt = cls.search_stmt(search, stmt=stmt)

        # print(len(session.execute(stmt).scalars().all()), stmt)

        global_filter: Union[str, None] = None
        if filters is not None:
            if "global" in filters.keys():
                global_filter = filters.pop("global")
            stmt = stmt.filter_by(**filters)

        # print(len(session.execute(stmt).scalars().all()), stmt)

        stmt = stmt.outerjoin(ModuleFilterSession, and_(ModuleFilterSession.module_id == cls.id,
                                                        ModuleFilterSession.user_id == user_id))
        # if session exists for another user, would it pick it up???

        # print(len(session.execute(stmt).all()))

        stmt = stmt.filter(or_(ModuleFilterSession.hidden.in_((True, None))))

        # print(len(session.execute(stmt).scalars().all()), stmt)

        if global_filter is not None:
            stmt = stmt.filter_by(**{global_filter: True})

        if sort == SortType.POPULARITY:  # reverse?
            stmt = stmt.order_by(cls.views)
        elif sort == SortType.CREATION_DATE:
            stmt = stmt.order_by(cls.created.desc())
        elif sort == SortType.VISIT_DATE:
            stmt = stmt.order_by(ModuleFilterSession.last_visited.desc())

        # print(len(session.execute(stmt.offset(offset).limit(limit)).scalars().all()), stmt)
        # print(stmt)
        # print(session.execute(stmt.offset(offset).limit(limit)).first())

        return session.get_paginated_rows(stmt, offset, limit)

    @classmethod
    def get_hidden_module_list(cls, session: sessionmaker, user_id: int, offset: int, limit: int) -> list[Row]:
        stmt = select(*cls.__table__.columns, Author.pseudonym)
        stmt = stmt.join(ModuleFilterSession, and_(ModuleFilterSession.module_id == cls.id,
                                                   ModuleFilterSession.user_id == user_id,
                                                   ModuleFilterSession.hidden.is_(True)))
        stmt = stmt.order_by(ModuleFilterSession.last_changed.desc())
        # print(*[(mfs.module_id, mfs.user_id, mfs.last_changed.isoformat())
        #         for mfs in session.execute(select(ModuleFilterSession)).scalars().all() if mfs.hidden], sep="\n")
        # print(stmt)
        return session.get_paginated_rows(stmt, offset, limit)

    def execute_point(self, point_id: int = None, theory_level: float = None) -> int:
        if point_id is None:
            point_id = randint(0, self.length - 1)

        point: Point = self.points[point_id]

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
