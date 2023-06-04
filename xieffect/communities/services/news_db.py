from __future__ import annotations

from typing import Self

from flask_fullstack import PydanticModel, Identifiable
from sqlalchemy import Column, ForeignKey, sql
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import Integer, String, Text, DateTime

from common import User
from common.abstract import SoftDeletable
from communities.base.meta_db import Community


class Post(SoftDeletable, Identifiable):
    __tablename__ = "cs_posts"
    not_found_text = "Post not found"

    # Vital
    id = Column(Integer, primary_key=True)
    title = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    created = Column(DateTime, server_default=sql.func.now(), nullable=False)
    changed = Column(
        DateTime,
        server_default=sql.func.now(),
        server_onupdate=sql.func.now(),
        nullable=False,
    )

    # User-related
    user_id = Column(
        Integer,
        ForeignKey(User.id, ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    user = relationship("User")

    # Community-related
    community_id = Column(
        Integer,
        ForeignKey(Community.id, ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    community = relationship("Community")

    BaseModel = PydanticModel.column_model(id)
    CreationBaseModel = PydanticModel.column_model(title, description)
    IndexModel = BaseModel.column_model(
        created, changed, community_id, user_id
    ).combine_with(CreationBaseModel)

    @classmethod
    def find_by_community(
        cls, community_id: int, offset: int, limit: int
    ) -> list[Self]:  # pragma: no coverage
        return cls.find_paginated_not_deleted(offset, limit, community_id=community_id)

    @classmethod
    def create(
        cls,
        title: str,
        description: str | None,
        user_id: int,
        community_id: int,
    ) -> Self:
        return super().create(
            title=title,
            description=description,
            user_id=user_id,
            community_id=community_id,
        )

    @classmethod
    def find_by_id(cls, entry_id: int) -> Self | None:
        return cls.find_first_not_deleted(id=entry_id)
