from main import db
from database.base.basic import UserRole, Identifiable


association_table = db.Table(
    "teams",
    db.Column("author_id", db.Integer, db.ForeignKey("authors.id"), primary_key=True),
    db.Column("team_id", db.Integer, db.ForeignKey("author-teams.id"), primary_key=True)
)


class Author(db.Model, UserRole):
    __tablename__ = "authors"
    not_found_text = "Author does not exist"

    id = db.Column(db.Integer, primary_key=True)
    teams = db.relationship("AuthorTeam", secondary=association_table, back_populates="members")
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


class AuthorTeam(db.Model, Identifiable):
    __tablename__ = "author-teams"
    not_found_text = "Team does not exist"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    members = db.relationship("Author", secondary=association_table, back_populates="teams")
    courses = db.relationship("Course", backref="author-teams")
    wip_courses = db.relationship("CATCourse", backref="author-teams")

    @classmethod
    def find_by_id(cls, team_id):
        return cls.query.filter_by(id=team_id).first()

    @classmethod
    def create(cls, name: str):
        new_entry = cls(name=name)
        db.session.add(new_entry)
        db.session.commit()
        return new_entry

    def get_owned_courses(self, start: int = 0, finish: int = None) -> list:
        pass

    def to_json(self):
        return {"id": self.id, "name": self.name}
