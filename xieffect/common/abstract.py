from __future__ import annotations

from common._core import Base  # noqa: WPS436


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
        prev_node: LinkedListNode | None,
        next_node: LinkedListNode | None,
        node: LinkedListNode = None,
    ) -> None:
        if prev_node is not None:
            prev_node.next_id = cls.get_node_id(node) or cls.get_node_id(next_node)
        if next_node is not None:
            next_node.prev_id = cls.get_node_id(node) or cls.get_node_id(prev_node)

    @classmethod
    def find_last(cls) -> LinkedListNode | None:
        return cls.find_first_by_kwargs(user_id=cls.user_id, next=None)

    @classmethod
    def find_prev(
        cls,
        entry_id: int | None,
    ) -> tuple[LinkedListNode, LinkedListNode]:
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
    ) -> LinkedListNode:
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

    def move(self, next_node: int | None) -> LinkedListNode:
        self.remove()
        return self.insert(next_node)

    def delete(self) -> None:
        self.remove()
        super().delete()
