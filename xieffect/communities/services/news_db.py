from __future__ import annotations

from sqlalchemy import Column, select, ForeignKey, sql
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql.sqltypes import Integer, String, Boolean, Text, DateTime

from __lib__.flask_fullstack import PydanticModel, Identifiable
from common import Base, sessionmaker, User
from communities.base.meta_db import Community


class Post(Base, Identifiable):
    __tablename__ = "cs_posts"

    # Vital
    id = Column(Integer, primary_key=True)
    title = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    create_datetime = Column(DateTime, server_default=sql.func.now())
    change_datetime = Column(DateTime, server_default=sql.func.now(), server_onupdate=sql.func.now())
    deleted = Column(Boolean, default=False)

    # User-related
    user_id = Column(Integer, ForeignKey(User.id), nullable=False)
    user = relationship("User", backref='posts')

    # Community-related
    community_id = Column(Integer, ForeignKey(Community.id), nullable=False)
    community = relationship("Community", backref=backref("Post", cascade="all, delete, delete-orphan"))

    MainData = PydanticModel.column_model(id, title, description, create_datetime, change_datetime, deleted,
                                          user_id, community_id)

    # Find a paginated list of community news
    @classmethod
    def find_by_community(cls, session: sessionmaker, community_id: int, offset: int, limit: int) -> list[Post] | None:
        return session.get_paginated(select(cls).filter_by(community_id=community_id), offset, limit)

    # Create news
    @classmethod
    def create(cls, session: sessionmaker, title: str, description: str | None, user_id: int,
               community_id: int) -> Post:
        entry: cls = super().create(session, title=title, description=description, user_id=user_id,
                                    community_id=community_id)
        return entry

    # Find list of community news by id
    @classmethod
    def find_by_id(cls, session: sessionmaker, entry_id: int) -> Post | None:
        return session.get_first(select(cls).filter_by(id=entry_id))
