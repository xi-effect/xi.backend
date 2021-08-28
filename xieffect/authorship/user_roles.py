from componets import UserRole
from main import db


class Author(db.Model, UserRole):
    __tablename__ = "authors"
    not_found_text = "Author does not exist"

    id = db.Column(db.Integer, primary_key=True)
    pseudonym = db.Column(db.String(100), nullable=False)
    banned = db.Column(db.Boolean, nullable=False, default=False)

    modules = db.relationship("Module", backref="authors")

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

    def get_owned_modules(self, start: int = 0, finish: int = None) -> list:
        pass

    def get_wip_courses(self, start: int = 0, finish: int = None) -> list:
        pass

    def get_owned_pages(self, start: int = 0, finish: int = None) -> list:
        pass


class Moderator(db.Model, UserRole):
    __tablename__ = "moderators"
    not_found_text = "Permission denied"

    id = db.Column(db.Integer, primary_key=True)

    @classmethod
    def find_by_id(cls, entry_id: int):
        return cls.query.filter_by(id=entry_id).first()

    @classmethod
    def create(cls, user_id: int) -> bool:
        if cls.find_by_id(user_id):
            return False
        new_entry = cls(id=user_id)
        db.session.add(new_entry)
        db.session.commit()
        return True
