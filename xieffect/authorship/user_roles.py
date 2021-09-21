from sqlalchemy import Column
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import Integer, String, Boolean

from componets import UserRole
from main import Base


class Author(Base, UserRole):
    __tablename__ = "authors"
    not_found_text = "Author does not exist"

    id = Column(Integer, primary_key=True)
    pseudonym = Column(String(100), nullable=False)
    banned = Column(Boolean, nullable=False, default=False)
    last_image_id = Column(Integer, nullable=False, default=0)

    modules = relationship("Module", backref="authors")

    @classmethod
    def create(cls, user):  # User class
        new_entry = cls(id=user.id, pseudonym=user.username)
        db.session.add(new_entry)
        db.session.commit()
        return new_entry

    @classmethod
    def find_by_id(cls, entry_id: int, include_banned: bool = False):
        return cls.query.filter_by(id=entry_id).first() if include_banned else \
            cls.query.filter_by(banned=False, id=entry_id).first()

    @classmethod
    def find_or_create(cls, user):  # User class
        if (author := cls.find_by_id(user.id, True)) is None:
            author = cls.create(user)
        return author

    def get_next_image_id(self):
        self.last_image_id += 1
        db.session.commit()
        return self.last_image_id


class Moderator(Base, UserRole):
    __tablename__ = "moderators"
    not_found_text = "Permission denied"

    id = Column(Integer, primary_key=True)

    @classmethod
    def find_by_id(cls, entry_id: int):
        return cls.query.filter_by(id=entry_id).first()

    @classmethod
    def create(cls, user_id: int) -> bool:
        if cls.find_by_id(user_id):
            return False
        new_entry = cls(id=user_id)
        session.add(new_entry)
        session.commit()
        return True
