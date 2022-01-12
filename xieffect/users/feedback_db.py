from __future__ import annotations

from json import dumps

from sqlalchemy import Column, select
from sqlalchemy.engine import Row
from sqlalchemy.sql.sqltypes import Integer, JSON, Enum

from common import create_marshal_model, Marshalable, TypeEnum, User
from main import Base, Session


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
    def create(cls, session: Session, user: User, feedback_type: FeedbackType, data) -> Feedback:
        new_user = cls(user_id=user.id, type=feedback_type, data=dumps(data, ensure_ascii=False))  # noqa
        session.add(new_user)
        return new_user

    @classmethod
    def find_by_id(cls, session: Session, entry_id: int) -> list[Feedback]:
        return session.execute(select(cls).where(cls.id == entry_id)).scalars().first()

    @classmethod
    def dump_all(cls, session: Session) -> list[Row]:
        stmt = select(*cls.__table__.columns, *User.__table__.columns).outerjoin(User, User.id == cls.user_id)
        return session.execute(stmt).all()


class FeedbackImage(Base):
    __tablename__ = "feedback-images"

    id = Column(Integer, primary_key=True)

    @classmethod
    def create(cls, session: Session) -> FeedbackImage:
        session.add(new_user := cls())
        session.flush()
        return new_user
