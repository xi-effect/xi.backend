from __future__ import annotations

from flask_fullstack import PydanticModel, Identifiable
from sqlalchemy import Column, select, ForeignKey, sql
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql.sqltypes import Integer, String, Boolean, Text, DateTime

from common import Base, db, User
from ..base.meta_db import Community


class Post(Base, Identifiable):
    __tablename__ = "cs_posts"
    not_found_text = "Post not found"

    # Vital
    id = Column(Integer, primary_key=True)
    title = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    created = Column(DateTime, server_default=sql.func.now(), nullable=False)
    changed = Column(
        DateTime, server_default=sql.func.now(),
        server_onupdate=sql.func.now(),
        nullable=False,
    )
    deleted = Column(Boolean, default=False, nullable=False)

    # User-related
    user_id = Column(Integer, ForeignKey(User.id), nullable=False)
    user = relationship("User", backref="posts")

    # Community-related
    community_id = Column(Integer, ForeignKey(Community.id), nullable=False)
    community = relationship(
        "Community", backref=backref("Post", cascade="all, delete, delete-orphan")
    )

    BaseModel = PydanticModel.column_model(id)
    CreationBaseModel = PydanticModel.column_model(title, description)
    IndexModel = BaseModel.column_model(
        created, changed, community_id, user_id
    ).combine_with(CreationBaseModel)

    @classmethod
    def find_by_community(
        cls, community_id: int, offset: int, limit: int
    ) -> list[Post]:
        stmt = select(cls).filter_by(community_id=community_id, deleted=False)
        return db.session.get_paginated(stmt, offset, limit)

    @classmethod
    def create(
        cls,
        title: str,
        description: str | None,
        user_id: int,
        community_id: int,
    ) -> Post:
        return super().create(
            title=title,
            description=description,
            user_id=user_id,
            community_id=community_id,
        )

    @classmethod
    def find_by_id(cls, entry_id: int) -> Post | None:
        return db.session.get_first(select(cls).filter_by(id=entry_id, deleted=False))
