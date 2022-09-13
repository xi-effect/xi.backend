from __future__ import annotations

from collections.abc import Callable
from json import dump as dump_json
from os import remove

from sqlalchemy import Column
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import Integer, String, Text, Enum

from common import Identifiable, TypeEnum, PydanticModel, db
from education.authorship.user_roles_db import Author, Base
from ..knowledge import PageKind, ModuleType


class WIPStatus(TypeEnum):
    WIP = 0
    PUBLISHED = 1


class CATFile(Base, Identifiable):
    __abstract__ = True
    mimetype: str = ""
    directory: str = "../files/tfs/other/"

    id = Column(Integer, primary_key=True)
    owner = Column(Integer, nullable=False, default=0)  # ForeignKey("authors.id"),
    # TODO add relation to author

    status = Column(Enum(WIPStatus), nullable=False)

    BaseModel = PydanticModel.column_model(status=status, id=id)

    @classmethod
    def _create(cls, owner: Author) -> CATFile:
        return cls(owner=owner.id, status=WIPStatus.WIP)

    @classmethod
    def create(cls, owner: Author) -> CATFile:
        entry: cls = cls._create(owner)
        db.session.add(entry)
        db.session.flush()
        return entry

    @classmethod
    def create_with_file(cls, owner: Author, data: bytes) -> CATFile:
        entry: cls = cls._create(owner)
        entry.update(data)
        db.session.add(entry)
        db.session.flush()
        return entry

    @classmethod
    def find_by_id(cls, entry_id: int) -> CATFile | None:
        return cls.find_first_by_kwargs(id=entry_id)

    @classmethod
    def find_by_owner(cls, owner: Author, start: int, limit: int) -> list[CATFile]:
        return cls.find_paginated_by_kwargs(start, limit, owner=owner.id)

    def get_link(self) -> str:
        if self.mimetype == "":
            return ""
        return f"{self.directory}/{self.id}.{self.mimetype}"

    def update(self, data: bytes) -> None:
        with open(self.get_link(), "wb") as f:
            f.write(data)

    def delete(self) -> None:
        remove(self.get_link())
        super().delete()


class JSONFile(CATFile):
    __abstract__ = True
    mimetype: str = "json"

    @classmethod
    def create_from_json(
        cls,
        owner: Author,
        json_data: dict,
    ) -> CATFile:
        file_id = json_data.get("id")
        entry = None if file_id is None else cls.find_by_id(json_data["id"])

        if entry is None:
            entry = cls._create(owner)
            entry.update_json(json_data)
        return entry

    def update_json(self, json_data: dict) -> None:
        self.update_metadata(json_data)
        db.session.add(self)
        db.session.flush()

        json_data["id"] = self.id
        with open(self.get_link(), "w", encoding="utf8") as f:
            dump_json(json_data, f, ensure_ascii=False)

    def update_metadata(self, json_data: dict) -> None:
        raise NotImplementedError


class WIPPage(JSONFile):
    __tablename__ = "wip-pages"
    not_found_text = "Page not found"
    directory: str = "../files/tfs/wip-pages/"

    kind = Column(Enum(PageKind), nullable=False)

    name = Column(String(100), nullable=False)
    theme = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    page = relationship("Page", backref="wip", uselist=False, cascade="all, delete")

    @PydanticModel.include_columns(kind, name, theme, description)
    class FullModel(CATFile.BaseModel):
        views: int = None

        @classmethod
        def callback_convert(cls, callback: Callable, orm_object: WIPPage, **_) -> None:
            callback(views=orm_object.views())

    def update_metadata(self, json_data: dict) -> None:
        self.kind = PageKind.from_string(json_data["kind"])
        self.name = json_data["name"]
        self.theme = json_data["theme"]
        self.description = json_data["description"]

    def views(self) -> int | None:
        return None if self.page is None else self.page.views


class WIPModule(JSONFile):
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

    @PydanticModel.include_columns(name, type, theme, category, difficulty, description)
    class FullModel(CATFile.BaseModel):
        views: int = None

        @classmethod
        def callback_convert(
            cls, callback: Callable, orm_object: WIPModule, **_
        ) -> None:
            callback(views=orm_object.views())

    def update_metadata(self, json_data: dict) -> None:
        self.type = ModuleType.from_string(json_data["type"])
        self.name = json_data["name"]
        self.description = json_data["description"]

        self.theme = json_data["theme"]
        self.category = json_data["category"]
        self.difficulty = json_data["difficulty"]

    def views(self) -> int | None:
        return None if self.module is None else self.module.views
