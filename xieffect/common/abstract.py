from __future__ import annotations

from common._core import Base, db  # noqa: WPS436


class LinkedListNode(Base):  # TODO pragma: no coverage
    __abstract__ = True

    @classmethod
    def add(
        cls,
        next_id: int | None,
        **kwargs,
    ) -> LinkedListNode:
        prev_node, next_node = cls.find_prev(next_id)
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
    def find_last(cls) -> LinkedListNode | None:
        return cls.find_first_by_kwargs(user_id=cls.user_id, next=None)

    def insert(
        self,
        next_id: int | None,
    ) -> LinkedListNode:
        prev_node, next_node = self.find_prev(next_id)
        self.next = next_node
        self.prev = prev_node
        db.session.flush()
        self.stitch(prev_node, next_node, self)
        return self

    @classmethod
    def find_prev(
        cls,
        entry_id: int | None,
    ) -> list[LinkedListNode]:
        next_node = cls.find_first_by_kwargs(id=entry_id)
        if next_node is None:
            prev_node = cls.find_last()
        else:
            prev_node = next_node.prev
        return [prev_node, next_node]

    def remove(self) -> None:
        removed_node = self.find_first_by_kwargs(id=self.id)
        prev_node = removed_node.prev
        next_node = removed_node.next
        self.stitch(prev_node, next_node)

    def move(self, next_node: int | None) -> LinkedListNode:
        self.remove()
        return self.insert(next_node)

    def delete(self) -> None:
        self.remove()
        super().delete()
