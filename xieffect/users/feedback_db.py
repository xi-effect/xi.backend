from __future__ import annotations

from flask_fullstack import PydanticModel, TypeEnum, Identifiable
from sqlalchemy import Column, select, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import Integer, JSON, Enum

from common import User, Base, db
from vault import File


class FeedbackImage(Base):
    __tablename__ = "feedback_images"

    feedback_id = Column(Integer, ForeignKey("feedbacks.id"), primary_key=True)
    file_id = Column(Integer, ForeignKey("files.id"), primary_key=True)


class FeedbackType(TypeEnum):
    GENERAL = 0
    BUG_REPORT = 1
    CONTENT_REPORT = 2


class Feedback(Base, Identifiable):
    __tablename__ = "feedbacks"
    not_found_text = "Feedback does not exist"

    id = Column(Integer, primary_key=True)
    type = Column(Enum(FeedbackType), nullable=False)
    data = Column(JSON, nullable=False)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user = relationship(User)

    files = relationship(
        "File",
        secondary=FeedbackImage.__table__,
        backref="feedbacks",
    )

    # fmt: off
    # TODO black should fix https://github.com/psf/black/issues/571
    FullModel = (
        PydanticModel
        .column_model(id, user_id, type, data)
        .nest_model(User.ProfileData, "user")
        .nest_model(File.FullModel, "files", as_list=True)
    )

    # fmt: on

    def add_files(self, files: list[File]) -> None:
        self.files.extend(files)
        db.session.flush()

    @classmethod
    def find_by_id(cls, entry_id: int) -> Feedback | None:
        return db.session.get_first(select(cls).filter_by(id=entry_id))

    @classmethod
    def search_by_params(
        cls,
        offset: int,
        limit: int,
        user_id: int | None,
        feedback_type: FeedbackType | None,
    ) -> list[Feedback]:
        stmt = select(cls)
        if user_id is not None:
            stmt = stmt.filter_by(user_id=user_id)
        if feedback_type is not None:
            stmt = stmt.filter_by(type=feedback_type)
        return db.session.get_paginated(stmt, offset, limit)
