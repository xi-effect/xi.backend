from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from sqlalchemy import Column, ForeignKey, select
from sqlalchemy.orm import relationship
from sqlalchemy.sql import Select
from sqlalchemy.sql.sqltypes import Integer, Boolean, JSON, DateTime, Text, Enum

from common import Identifiable, TypeEnum, Marshalable
from common import index_service, Base, db, PydanticModel
from ..authorship import Author


class PageKind(TypeEnum):
    THEORY = 0
    PRACTICE = 1


@index_service.register_as_searchable("name", "theme", "description")
class Page(Base, Identifiable, Marshalable):
    __tablename__ = "pages"
    not_found_text = "Page not found"

    id = Column(Integer, ForeignKey("wip-pages.id"), primary_key=True)
    author_id = Column(Integer, ForeignKey("authors.id"), nullable=False)
    author = relationship("Author")
    components = Column(JSON, nullable=False)

    kind = Column(Enum(PageKind), nullable=False)
    name = Column(Text, nullable=False)
    theme = Column(Text, nullable=False)
    description = Column(Text, nullable=True)

    reusable = Column(Boolean, nullable=False)
    public = Column(Boolean, nullable=False)
    blueprint = Column(Boolean, nullable=False)
    suspended = Column(Boolean, nullable=False, default=False)

    views = Column(Integer, nullable=False, default=0)
    updated = Column(DateTime, nullable=False)

    BaseModel = PydanticModel.column_model(id, name, kind, theme, description)
    MainModel = BaseModel.column_model(components)

    @PydanticModel.include_columns(author_id, views, updated)
    class ShortModel(BaseModel):
        author_name: str

        @classmethod
        def callback_convert(cls, callback: Callable, orm_object: Page, **_) -> None:
            callback(author_name=orm_object.author.pseudonym)

    @classmethod
    def _create(
        cls,
        json_data: dict[str, ...],
        author: Author,
    ) -> Page:
        json_data["kind"] = PageKind.from_string(json_data["kind"])
        entry: cls = cls(
            **{
                key: json_data[key]
                for key in (
                    "id",
                    "kind",
                    "name",
                    "theme",
                    "description",
                    "reusable",
                    "public",
                    "blueprint",
                )
            }
        )
        entry.components = json_data["components"]
        entry.updated = datetime.utcnow()
        entry.author = author
        db.session.add(entry)
        db.session.flush()
        return entry

    @classmethod
    def find_by_id(cls, entry_id: int) -> Page | None:
        return cls.find_first_by_kwargs(id=entry_id)

    @classmethod
    def find_or_create(
        cls,
        json_data: dict[str, ...],
        author: Author,
    ) -> Page | None:
        if cls.find_by_id(json_data["id"]):
            return None
        return cls._create(json_data, author)

    @classmethod
    def create_or_update(
        cls,
        json_data: dict[str, ...],
        author: Author = None,
    ) -> Page:
        # TODO utilize this, currently never used
        entry: cls
        if (entry := cls.find_by_id(json_data["id"])) is None:
            return cls._create(json_data, author)
        # redo... maybe...
        entry.delete()
        return cls._create(json_data, author)

    @classmethod
    def search(
        cls,
        search: str | None,
        start: int,
        limit: int,
    ) -> list[Page]:
        # TODO redo all search with pagination!!!
        stmt: Select = select(cls).filter_by(public=True)
        if search is not None and len(search) > 2:
            stmt = cls.search_stmt(search, stmt=stmt)
        return db.session.get_paginated(stmt, start, limit)

    def view(self) -> None:  # auto-commit
        self.views += 1
