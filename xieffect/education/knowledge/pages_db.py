from __future__ import annotations

from datetime import datetime
from json import dumps as json_dumps
from typing import Union

from sqlalchemy import Column, ForeignKey, select
from sqlalchemy.orm import relationship
from sqlalchemy.sql import Select
from sqlalchemy.sql.sqltypes import Integer, Boolean, JSON, DateTime, Text, Enum

from common import Identifiable, TypeEnum, create_marshal_model, Marshalable, LambdaFieldDef, register_as_searchable
from main import Base, Session
from ..authorship import Author


class PageKind(TypeEnum):
    THEORY = 0
    PRACTICE = 1


@register_as_searchable("name", "theme", "description")
@create_marshal_model("page-main", "components", inherit="page-base")
@create_marshal_model("page-short", "author_id", "views", "updated", inherit="page-base")
@create_marshal_model("page-base", "id", "name", "kind", "theme", "description")
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

    author_name: LambdaFieldDef = LambdaFieldDef("page-short", str, lambda page: page.author.pseudonym)

    @classmethod
    def _create(cls, session: Session, json_data: dict[str, ...], author: Author) -> Page:
        json_data["kind"] = PageKind.from_string(json_data["kind"])
        entry: cls = cls(**{key: json_data[key] for key in ("id", "kind", "name", "theme", "description",
                                                            "reusable", "public", "blueprint")})
        entry.components = json_dumps(json_data["components"], ensure_ascii=False)
        entry.updated = datetime.utcnow()
        entry.author = author
        session.add(entry)
        session.flush()
        return entry

    @classmethod
    def find_by_id(cls, session: Session, entry_id: int) -> Union[Page, None]:
        return session.execute(select(cls).where(cls.id == entry_id)).scalars().first()

    @classmethod
    def find_or_create(cls, session: Session, json_data: dict[str, ...], author: Author) -> Union[Page, None]:
        if cls.find_by_id(session, json_data["id"]):
            return None
        return cls._create(session, json_data, author)

    @classmethod
    def create_or_update(cls, session: Session, json_data: dict[str, ...], author: Author = None) -> Page:
        # TODO utilize this, currently never used
        entry: cls
        if (entry := cls.find_by_id(session, json_data["id"])) is None:
            return cls._create(session, json_data, author)
        else:  # redo... maybe...
            session.delete(entry)
            session.commit()
            cls._create(session, json_data, author)

    @classmethod
    def search(cls, session: Session, search: Union[str, None], start: int, limit: int) -> list[Page]:
        stmt: Select = select(cls).filter_by(public=True).offset(start).limit(limit)
        if search is not None and len(search) > 2:  # redo all search with pagination!!!
            stmt = cls.search_stmt(search, stmt=stmt)
        return session.execute(stmt).scalars().all()

    def view(self) -> None:  # auto-commit
        self.views += 1

    def delete(self, session: Session) -> None:
        session.delete(self)
        session.flush()
