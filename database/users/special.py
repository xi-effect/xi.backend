from database.base.basic import UserRole
from main import db


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
