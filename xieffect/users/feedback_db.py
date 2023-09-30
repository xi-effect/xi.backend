from __future__ import annotations

from typing import Self

from flask_fullstack import TypeEnum, Identifiable
from pydantic_marshals.sqlalchemy import MappedModel
from sqlalchemy import select, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql.sqltypes import JSON

from common import User, Base, db
from common.pydantic import v2_model_to_ffs
from vault import File


class FeedbackImage(Base):
    __tablename__ = "feedback_images"

    feedback_id: Mapped[int] = mapped_column(
        ForeignKey("feedbacks.id", ondelete="CASCADE"),
        primary_key=True,
    )
    file_id: Mapped[int] = mapped_column(
        ForeignKey("files.id", ondelete="CASCADE"),
        primary_key=True,
    )


class FeedbackType(TypeEnum):
    GENERAL = 0
    BUG_REPORT = 1
    CONTENT_REPORT = 2


class Feedback(Base, Identifiable):
    __tablename__ = "feedbacks"
    not_found_text = "Feedback does not exist"

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[FeedbackType] = mapped_column()
    data: Mapped[dict] = mapped_column(JSON)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    user: Mapped[User] = relationship(passive_deletes=True)

    files: Mapped[list[File]] = relationship(secondary=FeedbackImage.__table__)

    FullModel = MappedModel.create(
        columns=[id, user_id, type, data],
        relationships=[(user, User.ProfileData.raw), (files, File.FullModel.raw)],
    )

    def add_files(self, files: list[File]) -> None:
        self.files.extend(files)
        db.session.flush()

    @classmethod
    def find_by_id(cls, entry_id: int) -> Self | None:
        return db.get_first(select(cls).filter_by(id=entry_id))

    @classmethod
    def search_by_params(
        cls,
        offset: int,
        limit: int,
        user_id: int | None,
        feedback_type: FeedbackType | None,
    ) -> list[Self]:
        stmt = select(cls)
        if user_id is not None:
            stmt = stmt.filter_by(user_id=user_id)
        if feedback_type is not None:
            stmt = stmt.filter_by(type=feedback_type)
        return db.get_paginated(stmt, offset, limit)


Feedback.FullModel = v2_model_to_ffs(Feedback.FullModel)
