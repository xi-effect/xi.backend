from __future__ import annotations

from sqlalchemy import Column, select
from sqlalchemy.engine import Row
from sqlalchemy.sql.sqltypes import Integer, JSON, Enum

from common import create_marshal_model, Marshalable, TypeEnum, User, Base, sessionmaker


class FeedbackType(TypeEnum):
    GENERAL = 0
    BUG_REPORT = 1
    CONTENT_REPORT = 2


@create_marshal_model("feedback-full", "id", "user-id", "type", "data")
class Feedback(Base, Marshalable):
    __tablename__ = "feedbacks"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    type = Column(Enum(FeedbackType), nullable=False)
    data = Column(JSON, nullable=False)

    @classmethod
    def dump_all(cls, session: sessionmaker) -> list[Row]:
        stmt = select(*cls.__table__.columns, *User.__table__.columns).outerjoin(User, User.id == cls.user_id)
        return session.get_all_rows(stmt)


class FeedbackImage(Base):
    __tablename__ = "feedback-images"

    id = Column(Integer, primary_key=True)
