from __future__ import annotations

from sqlalchemy import Column, ForeignKey, select
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql.sqltypes import Integer, String, Text

from common import Base, Identifiable, db, PydanticModel

MAX_CHANNELS: int = 50


class ChannelCategory(Base, Identifiable):
    __tablename__ = "channel_categories"

    # Vital
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    # Previous category related
    prev_category_id = Column(Integer, ForeignKey("channel_categories.id"))
    prev_category = relationship(
        "ChannelCategory",
        remote_side=[id],
        foreign_keys=[prev_category_id],
    )

    # Next category related
    next_category_id = Column(Integer, ForeignKey("channel_categories.id"))
    next_category = relationship(
        "ChannelCategory",
        remote_side=[id],
        foreign_keys=[next_category_id],
    )

    # Community-related
    community_id = Column(Integer, ForeignKey("community.id"), nullable=False)
    community = relationship(
        "Community",
        backref=backref("categories", cascade="all, delete, delete-orphan")
    )

    BaseModel = PydanticModel.column_model(id)
    CreateModel = PydanticModel.column_model(name, description)
    IndexModel = BaseModel.column_model(
        prev_category_id,
        next_category_id,
    ).combine_with(CreateModel)

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
    def find_by_prev_id(cls, community_id, prev_id) -> ChannelCategory | None:
        stmt = select(cls).filter_by(
            community_id=community_id,
            prev_category_id=prev_id
        )
        return db.session.get_first(stmt)

    @classmethod
    def find_by_next_id(cls, community_id, next_id) -> ChannelCategory | None:
        stmt = select(cls).filter_by(
            community_id=community_id,
            next_category_id=next_id
        )
        return db.session.get_first(stmt)

    @classmethod
    def find_by_id(cls, entry_id: int) -> ChannelCategory | None:
        return db.session.get_first(select(cls).filter_by(id=entry_id))

# class ChannelType(TypeEnum):
#     NEWS = 1
#     TASKS = 2
#     CHAT = 3
#     ROOM = 4
#
#
# class Channel(Base, Identifiable):
#     __tablename__ = "channels"
#
#     global MAX_CHANNELS
#
#     # Vital
#     id = Column(Integer, primary_key=True)
#     name = Column(String(100), nullable=False)
#
#     type = Column(Enum(ChannelType))
#
#     # Previous channel related
#     prev_channel_id = Column(Integer, ForeignKey("channels.id"))
#     prev_channel = relationship(
#         "Channel",
#         remote_side=[id],
#         foreign_keys=[prev_channel_id]
#     )
#
#     # Next channel related
#     next_channel_id = Column(Integer, ForeignKey("channels.id"))
#     next_channel = relationship(
#         "Channel",
#         remote_side=[id],
#         foreign_keys=[next_channel_id]
#     )
