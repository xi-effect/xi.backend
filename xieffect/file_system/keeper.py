from enum import Enum
from json import dump
from os import remove
from typing import Dict, Union

from authorship import Author
from componets import Identifiable
from main import db


class Locations(Enum):
    SERVER = 0

    def to_link(self, file_type: str, file_id: int) -> str:
        result: str = ""
        if self == Locations.SERVER:
            result = f"files/tfs/{file_type}/{file_id}"

        return result


class CATFile(db.Model, Identifiable):
    __abstract__ = True

    id = db.Column(db.Integer, primary_key=True)
    owner = db.Column(db.Integer, nullable=False,  # db.ForeignKey("authors.id"),
                      default=0)  # test-only

    location = db.Column(db.Integer, nullable=False)
    status = db.Column(db.Integer, nullable=False)

    @classmethod
    def _create(cls, owner: Author):
        return cls(owner=owner.id, location=Locations.SERVER.value)

    def _add_to_db(self):
        db.session.add(self)
        db.session.commit()

    @classmethod
    def create(cls, owner: Author):
        entry: cls = cls.create(owner)
        entry._add_to_db()
        return entry

    @classmethod
    def create_with_file(cls, owner: Author, data: bytes):
        entry: cls = cls._create(owner)
        entry.update(data)
        entry._add_to_db()
        return entry

    @classmethod
    def find_by_id(cls, entry_id: int):
        return cls.query.filter_by(id=entry_id).first()

    @classmethod
    def find_by_owner(cls, owner: Author, start: int, limit: int) -> list:
        return cls.query.filter_by(owner=owner.id).offset(start).limit(limit).all()

    def update(self, data: bytes):
        with open(self.get_link(), "wb") as f:
            f.write(data)

    def get_link(self) -> str:
        return Locations(self.location).to_link(self.__tablename__, self.id)

    def delete(self):
        remove(self.get_link())
        db.session.delete(self)
        db.session.commit()


class Image(CATFile):
    __tablename__ = "images"
    not_found_text = "Image not found"


class JSONFile(CATFile):
    __abstract__ = True

    @classmethod
    def create_from_json(cls, owner: Author, json_data: dict):
        entry: cls = cls._create(owner)
        entry.update_json(json_data)
        return entry

    def get_link(self) -> str:
        return super().get_link() + ".json"

    def update_json(self, json_data: dict) -> None:
        self.update_metadata(json_data)
        self._add_to_db()

        with open(self.get_link(), "w", encoding="utf8") as f:
            dump(json_data, f, ensure_ascii=False)

    def update_metadata(self, json_data: dict) -> None:
        raise NotImplementedError

    def get_metadata(self) -> dict:
        raise NotImplementedError


class WIPPage(JSONFile):
    __tablename__ = "wip-pages"
    not_found_text = "Page not found"

    type = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    theme = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)

    reusable = db.Column(db.Boolean, nullable=False)
    public = db.Column(db.Boolean, nullable=False)
    published = db.Column(db.Boolean, nullable=False, default=False)

    def update_metadata(self, json_data: dict) -> None:
        self.type = json_data["type"]
        self.name = json_data["name"]
        self.theme = json_data["theme"]
        self.description = json_data["description"]
        self.reusable = json_data["reusable"]
        self.public = json_data["public"]

    def get_metadata(self) -> dict:
        return {"id": self.id, "type": self.type, "reusable": self.reusable, "public": self.public,
                "name": self.name, "theme": self.theme, "description": self.description}


class WIPModule(JSONFile):
    __tablename__ = "wip-modules"
    not_found_text = "Module not found"

    name = db.Column(db.String(100), nullable=False)

    def update_metadata(self, json_data: dict) -> None:
        self.name = json_data.pop("name")

    def get_metadata(self) -> Dict[str, Union[int, str]]:
        return {"id": self.id, "name": self.name}
