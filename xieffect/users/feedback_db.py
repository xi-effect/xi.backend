from __future__ import annotations

from sqlalchemy import Column, select, ForeignKey
from sqlalchemy.engine import Row
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import Integer, JSON, Enum

from __lib__.flask_fullstack import PydanticModel
from common import create_marshal_model, Marshalable, TypeEnum, User, Base, db


class FeedbackType(TypeEnum):
    GENERAL = 0
    BUG_REPORT = 1
    CONTENT_REPORT = 2


@create_marshal_model("feedback-full", "id", "user-id", "type", "data")
class Feedback(Base, Marshalable):
    __tablename__ = "feedbacks"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user = relationship(User)

    type = Column(Enum(FeedbackType), nullable=False)
    data = Column(JSON, nullable=False)

    # fmt: off
    # TODO black should fix https://github.com/psf/black/issues/571
    FullModel = (
        PydanticModel
        .column_model(id, user_id, type, data)
        .nest_model(User.FullData, "user")
    )

    # fmt: on

    @classmethod
    def dump_all(cls) -> list[Row]:
        return db.session.get_all(select(cls))


class FeedbackImage(Base):
    __tablename__ = "feedback-images"

    id = Column(Integer, primary_key=True)
