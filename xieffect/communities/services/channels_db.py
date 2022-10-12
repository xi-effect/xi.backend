from __future__ import annotations

from sqlalchemy import Column, ForeignKey, select, literal, func
from sqlalchemy.orm import relationship, backref, aliased
from sqlalchemy.sql.sqltypes import Integer, String, Text, Enum

from common import Base, Identifiable, db, PydanticModel, TypeEnum

MAX_CHANNELS: int = 50


class LinkedListNode(Base):
    __abstract__ = True

    @classmethod
    def add(
        cls,
        next_id: int | None,
        **kwargs,
    ) -> LinkedListNode:
        category_id = kwargs.get("category_id")
        prev_node, next_node = cls.find_prev(
            next_id,
            category_id,
            kwargs["community_id"],
        )
        added_node = cls.create(**kwargs)
        added_node.prev = prev_node
        added_node.next = next_node
        db.session.flush()
        cls.stitch(prev_node, next_node, added_node)
        return added_node

    @classmethod
    def stitch(
        cls,
        entry_prev_node: LinkedListNode,
        entry_next_node: LinkedListNode,
        node: LinkedListNode = None,
    ) -> None:
        next_node = node or entry_next_node
        prev_node = node or entry_prev_node

        if entry_prev_node is not None:
            if next_node is not None:
                next_node = next_node.id
            entry_prev_node.next_id = next_node
        if entry_next_node is not None:
            if prev_node is not None:
                prev_node = prev_node.id
            entry_next_node.prev_id = prev_node

    @classmethod
    def find_last(
        cls,
        category_id: int | None,
        community_id: int,
    ) -> LinkedListNode | None:
        if category_id is None:
            return cls.find_first_by_kwargs(community_id=community_id, next=None)
        else:
            return cls.find_first_by_kwargs(category_id=category_id, next=None)

    def insert(self,
               next_id: int | None,
               category_id: int | None,
               ) -> LinkedListNode:
        prev_node, next_node = self.find_prev(
            next_id,
            category_id,
            self.community_id,
        )
        self.next = next_node
        self.prev = prev_node
        db.session.flush()
        self.stitch(prev_node, next_node, self)
        return self

    @classmethod
    def find_prev(
        cls,
        entry_id: int | None,
        category_id: int | None,
        community_id: int,
    ) -> list[LinkedListNode]:
        next_node = cls.find_first_by_kwargs(
            community_id=community_id,
            id=entry_id,
        )
        if next_node is None:
            prev_node = cls.find_last(category_id, community_id)
        else:
            prev_node = next_node.prev
        return [prev_node, next_node]

    def remove(self) -> None:
        removed_node = self.find_first_by_kwargs(id=self.id)
        prev_node = removed_node.prev
        next_node = removed_node.next
        self.stitch(prev_node, next_node)

    def move(self, next_node: int | None, category_id=None) -> LinkedListNode:
        self.remove()
        return self.insert(next_node, category_id)

    def delete(self) -> None:
        self.remove()
        super().delete()


class Category(LinkedListNode, Identifiable):
    __tablename__ = "cs_categories"

    # Vital
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    # Previous category related
    prev_id = Column(
        Integer,
        ForeignKey("cs_categories.id"),
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
        ForeignKey("cs_categories.id"),
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


class Channel(LinkedListNode, Identifiable):
    __tablename__ = "cs_channels"

    # Vital
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    type = Column(Enum(ChannelType), nullable=False)

    # Local previous channel related
    prev_id = Column(Integer, ForeignKey("cs_channels.id"))
    prev = relationship(
        "Channel",
        remote_side=[id],
        foreign_keys=[prev_id],
    )

    # Local next channel related
    next_id = Column(Integer, ForeignKey("cs_channels.id"))
    next = relationship(
        "Channel",
        remote_side=[id],
        foreign_keys=[next_id],
    )

    # Global previous channel related
    global_prev_id = Column(Integer, ForeignKey("cs_channels.id"))
    global_prev = relationship(
        "Channel",
        remote_side=[id],
        foreign_keys=[global_prev_id],
    )

    # Global next channel related
    global_next_id = Column(Integer, ForeignKey("cs_channels.id"))
    global_next = relationship(
        "Channel",
        remote_side=[id],
        foreign_keys=[global_next_id],
    )

    # Category-related
    category_id = Column(
        Integer,
        ForeignKey("cs_categories.id", ondelete="SET NULL"),
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
    def bulk_add(cls, node):
        pass

    @classmethod
    def find_by_id(cls, entry_id: int) -> Channel | None:
        return db.session.get_first(select(cls).filter_by(id=entry_id))

    @classmethod
    def get_global_list(cls, community_id: int) -> list[Channel]:
        root = aliased(cls)
        node = aliased(cls)

        cte = select(root, literal(0).label("level")).filter_by(
            community_id=community_id,
            prev_id=None,
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

    @classmethod
    def get_local_list(cls, category_id: int) -> list[Channel]:
        root = aliased(cls)
        node = aliased(cls)

        cte = select(root, literal(0).label("level")).filter_by(
            category_id=category_id,
            prev_id=None,
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

    @classmethod
    def count_by_category(cls, category_id: int):
        return db.session.get_first(select(func.count(cls.id)).filter_by(
            category_id=category_id
        ))
