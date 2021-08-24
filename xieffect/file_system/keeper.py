from abc import ABC
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
            result = f"files/tfs/{file_type}/{file_id}/"

        return result


class CATFile(db.Model, Identifiable):
    __abstract__ = True

    id = db.Column(db.Integer, primary_key=True)
    owner = db.Column(db.Integer, db.ForeignKey("authors.id"), nullable=False,
                      default=0)  # test-only
    location = db.Column(db.Integer, nullable=False)

    @classmethod
    def create(cls, owner: Author):
        return cls(owner=owner, location=Locations.SERVER)

    @classmethod
    def create_with_file(cls, owner: Author, data: bytes):
        entry: cls = cls.create(owner)
        entry.update(data)
        return entry

    @classmethod
    def find_by_id(cls, entry_id: int):
        return cls.query.filter_by(id=entry_id).first()

    @classmethod
    def find_by_owner(cls, owner: Author, start: int, limit: int) -> list:
        return cls.query.filter_by(owner=owner).offset(start).limit(limit).all()

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


class JSONFile(CATFile, ABC):
    __abstract__ = True

    @classmethod
    def create_from_json(cls, owner: Author, json_data: dict):
        entry: cls = cls.create(owner)

        entry.update_metadata(json_data)
        db.session.commit()

        with open(entry.get_link(), "wb") as f:
            dump(json_data, f)
        return entry

    def update_json(self, json_data: dict):
        with open(self.get_link(), "wb") as f:
            dump(json_data, f)

        self.update_metadata(json_data)
        db.session.commit()

    def update_metadata(self, json_data: dict):
        raise NotImplementedError

    def get_metadata(self) -> str:
        raise NotImplementedError


class WIPPage(JSONFile):
    __tablename__ = "pages"
    not_found_text = "Page not found"

    tags = db.Column(db.String(100), nullable=False)
    reusable = db.Column(db.Boolean, nullable=False)
    published = db.Column(db.Boolean, nullable=False)

    def update_metadata(self, json_data: dict):
        pass

    def get_metadata(self) -> str:
        pass


class WIPModule(JSONFile):
    __tablename__ = "pages"
    not_found_text = "Module not found"

    name = db.Column(db.String(100), nullable=False)

    def update_metadata(self, json_data: dict):
        self.name = json_data["name"]

    def get_metadata(self) -> Dict[str, Union[int, str]]:
        return {"id": self.id, "name": self.name}
