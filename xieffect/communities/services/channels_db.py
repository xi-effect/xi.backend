from __future__ import annotations

from sqlalchemy import Column, ForeignKey, select
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql.sqltypes import Integer, String, Text, Enum

from common import Base, Identifiable, db, PydanticModel, TypeEnum

MAX_CHANNELS: int = 50


class ChannelCategory(Base, Identifiable):
    __tablename__ = "channel_categories"

    # Vital
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    # Previous category related
    prev_category_id = Column(
        Integer,
        ForeignKey("channel_categories.id"),
        nullable=True,
    )
    prev_category = relationship(
        "ChannelCategory",
        remote_side=[id],
        foreign_keys=[prev_category_id],
    )

    # Next category related
    next_category_id = Column(
        Integer,
        ForeignKey("channel_categories.id"),
        nullable=True,
    )
    next_category = relationship(
        "ChannelCategory",
        remote_side=[id],
        foreign_keys=[next_category_id],
    )

    # Community-related
    community_id = Column(Integer, ForeignKey("community.id"), nullable=False)
    community = relationship(
        "Community",
        backref=backref("categories", cascade="all, delete, delete-orphan"),
    )

    BaseModel = PydanticModel.column_model(id)
    CreateModel = PydanticModel.column_model(name, description)
    IndexModel = BaseModel.combine_with(CreateModel)

    @classmethod
    def create(
        cls,
        name: str,
        description: str | None,
        prev_category_id: int | None,
        next_category_id: int | None,
        community_id: int,
    ) -> ChannelCategory:
        return super().create(
            name=name,
            description=description,
            prev_category_id=prev_category_id,
            next_category_id=next_category_id,
            community_id=community_id,
        )

    @classmethod
    def find_by_next_id(cls, community_id: int, next_id: int | None) -> ChannelCategory | None:
        stmt = select(cls).filter_by(
            community_id=community_id,
            next_category_id=next_id,
        )
        return db.session.get_first(stmt)

    @classmethod
    def find_by_id(cls, entry_id: int) -> ChannelCategory | None:
        return db.session.get_first(select(cls).filter_by(id=entry_id))


class ChannelType(TypeEnum):
    NEWS = 1
    TASKS = 2
    CHAT = 3
    ROOM = 4


class Channel(Base, Identifiable):
    __tablename__ = "channels"

    # Vital
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)

    type = Column(Enum(ChannelType), nullable=False)

    # Previous channel related
    prev_channel_id = Column(Integer, ForeignKey("channels.id"))
    prev_channel = relationship(
        "Channel",
        remote_side=[id],
        foreign_keys=[prev_channel_id],
    )

    # Next channel related
    next_channel_id = Column(Integer, ForeignKey("channels.id"))
    next_channel = relationship(
        "Channel",
        remote_side=[id],
        foreign_keys=[next_channel_id],
    )

    # Category-related
    category_id = Column(
        Integer,
        ForeignKey("channel_categories.id"),
        nullable=True,
    )
    category = relationship("ChannelCategory", backref=backref("channels"))

    @classmethod
    def create(
        cls,
        name: str,
        type: ChannelType,
        prev_channel_id: int | None,
        next_channel_id: int | None,
        category_id: int | None,
    ) -> Channel:
        return super().create(
            name=name,
            type=type,
            prev_channel_id=prev_channel_id,
            next_channel_id=next_channel_id,
            category_id=category_id,
        )

    @classmethod
    def find_by_next_id(cls, category_id: int | None, next_id: int | None) -> Channel | None:
        stmt = select(cls).filter_by(
            category_id=category_id,
            next_channel_id=next_id,
        )
        return db.session.get_first(stmt)

    @classmethod
    def find_by_id(cls, entry_id: int) -> Channel | None:
        return db.session.get_first(select(cls).filter_by(id=entry_id))
