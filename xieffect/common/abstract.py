from __future__ import annotations

from datetime import datetime, timedelta
from typing import Self

from sqlalchemy import Column, DateTime
from sqlalchemy.sql import Select

from common._core import Base  # noqa: WPS436


class SoftDeletable(Base):
    __abstract__ = True

    deleted = Column(DateTime, nullable=True)
    shelf_life: timedelta = timedelta(days=2)  # TODO: discuss timedelta for each table

    def soft_delete(self) -> None:
        self.deleted = datetime.utcnow() + self.shelf_life  # noqa: WPS601

    @classmethod
    def find_first_not_deleted(cls, **kwargs) -> Self | None:
        return cls.find_first_by_kwargs(deleted=None, **kwargs)

    @classmethod
    def find_all_not_deleted(cls, **kwargs) -> list[Self]:
        return cls.find_all_by_kwargs(deleted=None, **kwargs)

    @classmethod
    def find_paginated_not_deleted(
        cls, offset: int, limit: int, *args, **kwargs
    ) -> list[Self]:  # pragma: no coverage
        return cls.find_paginated_by_kwargs(
            offset, limit, *args, deleted=None, **kwargs
        )

    @classmethod
    def select_not_deleted(cls) -> Select:
        return cls.select_by_kwargs(deleted=None)


class LinkedListNode(Base):
    __abstract__ = True

    @staticmethod
    def get_node_id(entry_node: LinkedListNode | None) -> int | None:
        if entry_node is None:
            return None
        return entry_node.id

    @classmethod
    def stitch(
        cls,
        prev_node: Self | None,
        next_node: Self | None,
        node: Self = None,
    ) -> None:
        if prev_node is not None:
            prev_node.next_id = cls.get_node_id(node) or cls.get_node_id(next_node)
        if next_node is not None:
            next_node.prev_id = cls.get_node_id(node) or cls.get_node_id(prev_node)

    @classmethod
    def find_last(cls) -> Self | None:
        return cls.find_first_by_kwargs(user_id=cls.user_id, next=None)

    @classmethod
    def find_prev(
        cls,
        entry_id: int | None,
    ) -> tuple[Self, Self]:
        next_node = cls.find_first_by_kwargs(id=entry_id)
        if next_node is None:
            prev_node = cls.find_last()
        else:
            prev_node = next_node.prev
        return prev_node, next_node

    @classmethod
    def add(
        cls,
        next_id: int = None,
        **kwargs,
    ) -> Self:
        prev_node, next_node = cls.find_prev(next_id)
        added_node = cls.create(**kwargs)
        added_node.prev_id = cls.get_node_id(prev_node)
        added_node.next_id = cls.get_node_id(next_node)
        cls.stitch(prev_node, next_node, added_node)
        return added_node

    def insert(
        self,
        next_id: int | None,
    ) -> LinkedListNode:
        prev_node, next_node = self.find_prev(next_id)
        self.next_id = self.get_node_id(next_node)
        self.prev_id = self.get_node_id(prev_node)
        self.stitch(prev_node, next_node, self)
        return self

    def remove(self) -> None:
        prev_node = self.prev
        next_node = self.next
        self.stitch(prev_node, next_node)

    def move(self, next_node: int | None) -> Self:
        self.remove()
        return self.insert(next_node)

    def delete(self) -> None:
        self.remove()
        super().delete()
