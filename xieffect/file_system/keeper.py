from enum import Enum
from json import dump, load
from os import remove
from typing import Dict, Union

from sqlalchemy import Column
from sqlalchemy.sql.sqltypes import Integer, String, Text

from authorship import Author
from componets import Identifiable
from education import Page
from main import Base, Session


class WIPStatus(Enum):
    WIP = 0
    PUBLISHED = 1


class CATFile(Base, Identifiable):
    __abstract__ = True
    mimetype: str = ""
    directory: str = "../files/tfs/other/"

    id = Column(Integer, primary_key=True)
    owner = Column(Integer, nullable=False,  # ForeignKey("authors.id"),
                   default=0)  # test-only

    status = Column(Integer, nullable=False)

    @classmethod
    def _create(cls, owner: Author):
        return cls(owner=owner.id, status=WIPStatus.WIP.value)

    def _add_to_db(self, session: Session):
        session.add(self)
        session.commit()

    @classmethod
    def create(cls, session: Session, owner: Author):
        entry: cls = cls.create(session, owner)
        entry._add_to_db(session)
        return entry

    @classmethod
    def create_with_file(cls, session: Session, owner: Author, data: bytes):
        entry: cls = cls._create(owner)
        entry.update(data)
        entry._add_to_db(session)
        return entry

    @classmethod
    def find_by_id(cls, session: Session, entry_id: int):
        return cls.query.filter_by(id=entry_id).first()

    @classmethod
    def find_by_owner(cls, session: Session, owner: Author, start: int, limit: int) -> list:
        return cls.query.filter_by(owner=owner.id).offset(start).limit(limit).all()

    def get_link(self) -> str:
        return f"{self.directory}/{self.id}" + f".{self.mimetype}" if self.mimetype != "" else ""

    def update(self, data: bytes):
        with open(self.get_link(), "wb") as f:
            f.write(data)

    def delete(self, session: Session):
        if (page := Page.find_by_id(session, self.id)) is not None:
            page.delete()
        remove(self.get_link())
        session.delete(self)
        session.commit()


class JSONFile(CATFile):
    __abstract__ = True
    mimetype: str = "json"

    @classmethod
    def create_from_json(cls, session: Session, owner: Author, json_data: dict):
        entry: cls = cls._create(owner)
        entry.update_json(session, json_data)
        return entry

    def update_json(self, session: Session, json_data: dict) -> None:
        self.update_metadata(json_data)
        self._add_to_db(session)

        json_data["id"] = self.id
        with open(self.get_link(), "w", encoding="utf8") as f:
            dump(json_data, f, ensure_ascii=False)

    def update_metadata(self, json_data: dict) -> None:
        raise NotImplementedError

    def get_metadata(self, session: Session) -> dict:
        raise NotImplementedError


class WIPPage(JSONFile):
    @staticmethod
    def create_test_bundle(session: Session, author: Author):
        for i in range(1, 4):
            with open(f"../files/tfs/test/{i}.json", "rb") as f:
                WIPPage.create_from_json(session, author, load(f))

    __tablename__ = "wip-pages"
    not_found_text = "Page not found"
    directory: str = "../files/tfs/wip-pages/"

    kind = Column(Integer, nullable=False)

    name = Column(String(100), nullable=False)
    theme = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    def update_metadata(self, json_data: dict) -> None:
        self.kind = json_data["kind"]
        self.name = json_data["name"]
        self.theme = json_data["theme"]
        self.description = json_data["description"]

    def get_metadata(self, session: Session) -> dict:
        return {"id": self.id, "kind": self.kind, "name": self.name, "theme": self.theme,
                "description": self.description, "status": WIPStatus(self.status).name.lower(),
                "views": page.views if (page := Page.find_by_id(session, self.id)) is not None else None}


class WIPModule(JSONFile):
    __tablename__ = "wip-modules"
    not_found_text = "Module not found"
    directory: str = "../files/tfs/wip-modules/"

    name = Column(String(100), nullable=False)

    def update_metadata(self, json_data: dict) -> None:
        self.name = json_data.pop("name")

    def get_metadata(self, session: Session) -> Dict[str, Union[int, str]]:
        return {"id": self.id, "name": self.name}
