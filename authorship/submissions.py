from datetime import datetime
from enum import Enum
# from typing import Set

# from flask_sqlalchemy import BaseQuery
from typing import Set

from flask_sqlalchemy import BaseQuery

from componets.basic import Identifiable
from main import db


class ModerationStatus(Enum):
    POSTED = 0
    BEING_REVIEWED = 1
    DENIED = 2
    PUBLISHED = 3


class CATSubmission(db.Model, Identifiable):
    __tablename__ = "cat-submissions"
    not_found_text = "Submission not found"

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.Integer, nullable=False)  # 0 - page, 1 - course
    status = db.Column(db.Integer, nullable=False, default=0)  # ModerationStatus
    entity_id = db.Column(db.Integer, nullable=False)
    author_id = db.Column(db.String(100), nullable=False)
    date = db.Column(db.DateTime, nullable=False)

    @classmethod
    def create(cls, author_id: int, submission_type: int, tags: str):
        new_entry = cls(author_id=author_id, date=datetime.utcnow(),
                        type=submission_type, tags=tags)
        db.session.add(new_entry)
        db.session.commit()
        return new_entry

    @classmethod
    def find_by_id(cls, entry_id: int):
        return cls.query.filter_by(id=entry_id).first()

    @classmethod
    def find_by_tags(cls, tags: Set[str], submission_type: int = None,
                     offset: int = 0, limit: int = None):
        query: BaseQuery = cls.query.filter_by(status=ModerationStatus.POSTED.value)
        if submission_type is not None:
            query = query.filter_by(type=submission_type)

        for i in range(len(tags)):
            query = query.filter(CATSubmission.tags.like(f"%{tags.pop()} %"))
        query = query.order_by(CATSubmission.date)

        if limit is not None:
            query = query.limit(limit)
        return query.offset(offset).all()

    @classmethod
    def find_by_author(cls, author_id: int, offset: int, limit: int):
        return cls.query\
            .filter_by(author_id=author_id)\
            .order_by(CATSubmission.date)\
            .offset(offset).limit(limit).all()

    @classmethod
    def list_unreviewed(cls, offset: int, limit: int):
        return cls.query\
            .filter_by(status=ModerationStatus.POSTED.value)\
            .order_by(CATSubmission.date)\
            .offset(offset).limit(limit).all()

    def to_author_json(self) -> dict:
        return {"id": self.id, "status": self.status}

    def to_moderator_json(self) -> dict:
        return {"id": self.id, "type": self.type, "tags": self.tags}

    def mark_read(self) -> bool:
        if ModerationStatus(self.status) == ModerationStatus.POSTED:
            self.status = ModerationStatus.BEING_REVIEWED.value
            return True
        return False

    def delete(self) -> bool:
        if ModerationStatus(self.status) in (ModerationStatus.DENIED, ModerationStatus.PUBLISHED):
            db.session.delete(self)
            db.session.commit()
            return True
        return False

    def review(self, published: bool):
        if published:
            self.status = ModerationStatus.PUBLISHED.value
        else:
            self.status = ModerationStatus.DENIED.value
