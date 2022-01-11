from __future__ import annotations

from json import dump
from os import remove
from typing import Union

from sqlalchemy import Column, select
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import Integer, String, Text, Enum

from common import Identifiable, TypeEnum, create_marshal_model, LambdaFieldDef, Marshalable
from education.authorship.user_roles_db import Author
from main import Base, Session
from ..knowledge import PageKind, ModuleType


class WIPStatus(TypeEnum):
    WIP = 0
    PUBLISHED = 1


class CATFile(Base, Identifiable):
    __abstract__ = True
    mimetype: str = ""
    directory: str = "../files/tfs/other/"

    id = Column(Integer, primary_key=True)
    owner = Column(Integer, nullable=False,  # ForeignKey("authors.id"),
                   default=0)  # TODO add relation to author

    status = Column(Enum(WIPStatus), nullable=False)

    @classmethod
    def _create(cls, owner: Author) -> CATFile:
        return cls(owner=owner.id, status=WIPStatus.WIP)

    @classmethod
    def create(cls, session: Session, owner: Author) -> CATFile:
        entry: cls = cls.create(session, owner)
        session.add(entry)
        session.flush()
        return entry

    @classmethod
    def create_with_file(cls, session: Session, owner: Author, data: bytes) -> CATFile:
        entry: cls = cls._create(owner)
        entry.update(data)
        session.add(entry)
        session.flush()
        return entry

    @classmethod
    def find_by_id(cls, session: Session, entry_id: int) -> Union[CATFile, None]:
        return session.execute(select(cls).where(cls.id == entry_id)).scalars().first()

    @classmethod
    def find_by_owner(cls, session: Session, owner: Author, start: int, limit: int) -> list[CATFile]:
        return session.execute(select(cls).where(cls.owner == owner.id).offset(start).limit(limit)).scalars().all()

    def get_link(self) -> str:
        return f"{self.directory}/{self.id}" + f".{self.mimetype}" if self.mimetype != "" else ""

    def update(self, data: bytes) -> None:
        with open(self.get_link(), "wb") as f:
            f.write(data)

    def delete(self, session: Session) -> None:
        remove(self.get_link())
        session.delete(self)
        session.flush()


class JSONFile(CATFile):
    __abstract__ = True
    mimetype: str = "json"

    @classmethod
    def create_from_json(cls, session: Session, owner: Author, json_data: dict) -> CATFile:
        if "id" not in json_data.keys() or (entry := cls.find_by_id(session, json_data["id"])) is None:
            entry: cls = cls._create(owner)
            entry.update_json(session, json_data)
        return entry

    def update_json(self, session: Session, json_data: dict) -> None:
        self.update_metadata(json_data)
        session.add(self)
        session.flush()

        json_data["id"] = self.id
        with open(self.get_link(), "w", encoding="utf8") as f:
            dump(json_data, f, ensure_ascii=False)

    def update_metadata(self, json_data: dict) -> None:
        raise NotImplementedError


@create_marshal_model("wip-page", "id", "kind", "name", "theme", "description", "status")
class WIPPage(JSONFile, Marshalable):
    __tablename__ = "wip-pages"
    not_found_text = "Page not found"
    directory: str = "../files/tfs/wip-pages/"

    kind = Column(Enum(PageKind), nullable=False)

    name = Column(String(100), nullable=False)
    theme = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    page = relationship("Page", backref="wip", uselist=False, cascade="all, delete")

    views: LambdaFieldDef = LambdaFieldDef("wip-page", int, lambda wip_page: wip_page.get_views())

    def update_metadata(self, json_data: dict) -> None:
        self.kind = PageKind.from_string(json_data["kind"])
        self.name = json_data["name"]
        self.theme = json_data["theme"]
        self.description = json_data["description"]

    def get_views(self) -> Union[int, None]:
        return None if self.page is None else self.page.views


@create_marshal_model("wip-module", "id", "name", "type", "theme", "category", "difficulty", "description", "status")
class WIPModule(JSONFile, Marshalable):
    __tablename__ = "wip-modules"
    not_found_text = "Module not found"
    directory: str = "../files/tfs/wip-modules/"

    # Essentials:
    type = Column(Enum(ModuleType), nullable=False)
    name = Column(Text, nullable=False)
    description = Column(Text, nullable=True)

    # Filtering:
    theme = Column(String(20), nullable=False)
    category = Column(String(20), nullable=False)
    difficulty = Column(String(20), nullable=False)

    module = relationship("Module", backref="wip", uselist=False, cascade="all, delete")

    views: LambdaFieldDef = LambdaFieldDef("wip-module", int,
                                           lambda wip_module: wip_module.get_views())

    def update_metadata(self, json_data: dict) -> None:
        self.type = ModuleType.from_string(json_data["type"])
        self.name = json_data["name"]
        self.description = json_data["description"]

        self.theme = json_data["theme"]
        self.category = json_data["category"]
        self.difficulty = json_data["difficulty"]

    def get_views(self) -> Union[int, None]:
        return None if self.module is None else self.module.views