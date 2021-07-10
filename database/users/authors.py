from main import db
from database.base.basic import UserRole


class Author(db.Model, UserRole):
    __tablename__ = "authors"
    not_found_text = "Author does not exist"

    id = db.Column(db.Integer, primary_key=True)
    modules = db.relationship("Module", backref="authors")
    pages = db.relationship("Page", backref="authors")

    @classmethod
    def create(cls, user_id: int):
        new_entry = cls(id=user_id)
        db.session.add(new_entry)
        db.session.commit()
        return new_entry

    @classmethod
    def find_by_id(cls, entry_id: int):
        return cls.query.filter_by(id=entry_id).first()

    def get_teams(self, start: int = 0, finish: int = None) -> list:
        return list(map(lambda x: x.to_json(), self.teams[start:finish]))

    def get_wip_courses(self, start: int = 0, finish: int = None) -> list:
        pass

    def get_owned_pages(self, start: int = 0, finish: int = None) -> list:
        pass
