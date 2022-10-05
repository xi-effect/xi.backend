from __future__ import annotations

from sqlalchemy import Column, ForeignKey, select, literal
from sqlalchemy.orm import relationship, backref, aliased
from sqlalchemy.sql.sqltypes import Integer, String, Text, Enum

from common import Base, Identifiable, db, PydanticModel, TypeEnum

MAX_CHANNELS: int = 50


class LinkedList(Base):
    __abstract__ = True

    @classmethod
    def find_last(cls, cid) -> LinkedList | None:
        return cls.find_first_by_kwargs(community_id=cid.community_id, next=None)

    @classmethod
    def stitch(cls, prev, next, cid=None) -> None:
        nid = cid or next
        pid = cid or prev

        if prev:
            if nid:
                nid = nid.id
            prev.next_id = nid
        if next:
            if pid:
                pid = pid.id
            next.prev_id = pid
        db.session.flush()

    @classmethod
    def insert(cls, cid, next) -> None:
        next = cls.find_first_by_kwargs(community_id=cid.community_id, id=next)
        if next:
            prev = next.prev
        else:
            prev = cls.find_last(cid)
        cid.next = next
        cid.prev = prev
        db.session.flush()
        cls.stitch(prev, next, cid)
        return cid

    @classmethod
    def add(cls, next, **kwargs):
        added = cls.create(**kwargs)
        cls.insert(added, next)
        return added

    @classmethod
    def remove(cls, cid) -> None:
        removed = cls.find_first_by_kwargs(id=cid.id)
        prev = removed.prev
        next = removed.next
        cls.stitch(prev, next)

    def deleter(self, cid):
        self.remove(cid)
        self.delete()

    @classmethod
    def move(cls, cid, next) -> LinkedList:
        cls.remove(cid)
        return cls.insert(cid, next)


class Category(LinkedList, Identifiable):
    __tablename__ = "categories"

    # Vital
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    # Previous category related
    prev_id = Column(
        Integer,
        ForeignKey("categories.id"),
        nullable=True,
    )
    prev = relationship(
        "Category",
        remote_side=[id],
        foreign_keys=[prev_id],
    )

    # Next category related
    next_id = Column(
        Integer,
        ForeignKey("categories.id"),
        nullable=True,
    )
    next = relationship(
        "Category",
        remote_side=[id],
        foreign_keys=[next_id],
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
    def find_by_id(cls, entry_id: int) -> Category | None:
        return db.session.get_first(select(cls).filter_by(id=entry_id))

    @classmethod
    def find_by_community(cls, community_id: int) -> list[Category]:
        root = aliased(cls)
        node = aliased(cls)

        cte = select(root, literal(0).label("level")).filter_by(
            community_id=community_id, prev_id=None
        ).cte("cte", recursive=True)

        result = cte.union_all(
            select(node, cte.c.level + 1)
            .join(cte, node.prev_id == cte.c.id)
        )

        return db.session.get_all(
            select(Category)
            .join(result, cls.id == result.c.id)
            .order_by(cte.c.level)
        )


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
    prev_id = Column(Integer, ForeignKey("channels.id"))
    prev = relationship(
        "Channel",
        remote_side=[id],
        foreign_keys=[prev_id],
    )

    # Next channel related
    next_id = Column(Integer, ForeignKey("channels.id"))
    next = relationship(
        "Channel",
        remote_side=[id],
        foreign_keys=[next_id],
    )

    # Category-related
    category_id = Column(
        Integer,
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
    )
    category = relationship("Category", backref=backref("channels"))

    # Community-related
    community_id = Column(Integer, ForeignKey("community.id"), nullable=False)
    community = relationship(
        "Community",
        backref=backref("channels", cascade="all, delete, delete-orphan"),
    )

    BaseModel = PydanticModel.column_model(id)
    CreateModel = PydanticModel.column_model(name, type)
    IndexModel = BaseModel.combine_with(CreateModel)

    @classmethod
    def create(
        cls,
        name: str,
        channel_type: ChannelType,
        prev_id: int | None,
        next_id: int | None,
        community_id: int,
        category_id: int | None,
    ) -> Channel:
        return super().create(
            name=name,
            type=channel_type,
            prev_id=prev_id,
            next_id=next_id,
            community_id=community_id,
            category_id=category_id,
        )

    @classmethod
    def find_by_next_id(
        cls,
        community_id: int,
        category_id: int | None,
        next_id: int | None
    ) -> Channel | None:
        return db.session.get_first(select(cls).filter_by(
            community_id=community_id,
            category_id=category_id,
            next_id=next_id,
        ))

    @classmethod
    def find_by_id(cls, entry_id: int) -> Channel | None:
        return db.session.get_first(select(cls).filter_by(id=entry_id))

    @classmethod
    def find_by_type(
        cls,
        community_id: int,
        category_id: int,
        channel_type: ChannelType
    ) -> list[Channel]:
        return db.session.get_all(select(cls).filter_by(
            community_id=community_id,
            category_id=category_id,
            type=channel_type,
        ))

    @classmethod
    def find_by_ids(cls, community_id: int, category_id: int | None) -> list[Channel]:
        root = aliased(cls)
        node = aliased(cls)

        cte = select(root, literal(0).label("level")).filter_by(
            community_id=community_id,
            category_id=category_id,
            prev_id=category_id,
        ).cte("cte", recursive=True)

        result = cte.union_all(
            select(node, cte.c.level + 1)
            .join(cte, node.prev_id == cte.c.id)
        )

        return db.session.get_all(
            select(Channel)
            .join(result, cls.id == result.c.id)
            .order_by(cte.c.level)
        )
