from __future__ import annotations

from sqlalchemy import Column, ForeignKey, select
from sqlalchemy.ext.orderinglist import ordering_list
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import Integer

from common import PydanticModel, Base, User, db
from communities.base.meta_db import Community


class CommunitiesUser(Base):
    __tablename__ = "communities_users"

    id: int | Column = Column(Integer, ForeignKey("users.id"), primary_key=True)
    user = relationship("User")

    communities = relationship(
        "CommunityListItem",
        order_by="CommunityListItem.position",
        collection_class=ordering_list("position"),
    )

    @PydanticModel.include_nest_model(User.MainData, "user")
    class FullModel(PydanticModel):
        communities: list[Community.IndexModel]

        @classmethod
        def callback_convert(cls, callback, orm_object: CommunitiesUser, **context):
            callback(
                communities=[
                    Community.IndexModel.convert(ci.community, **context)
                    for ci in orm_object.communities
                ]
            )

    class TempModel(FullModel):
        a: str = "Success"

    @classmethod
    def _create_empty(cls, user_id: int) -> CommunitiesUser:
        return cls.create(id=user_id)

    @classmethod
    def find_by_id(cls, user_id: int) -> CommunitiesUser | None:
        return db.session.get_first(select(cls).filter_by(id=user_id))

    @classmethod
    def find_or_create(cls, user_id: int) -> CommunitiesUser:
        return cls.find_by_id(user_id) or cls._create_empty(user_id)

    def reorder_community_list(
        self,
        source_id: int,
        target_index: int,
    ) -> bool:
        # TODO target_index might change after deletion?
        list_item = CommunityListItem.find_by_ids(self.id, source_id)
        if list_item is None:
            return False
        self.communities.remove(list_item)
        self.communities.insert(target_index, list_item)
        return True

    def join_community(self, community_id: int) -> None:
        # autocommit  # TODO find a way to reverse the list
        new_item = CommunityListItem(user_id=self.id, community_id=community_id)
        self.communities.insert(0, new_item)

    def leave_community(self, community_id: int) -> bool:
        list_item = CommunityListItem.find_by_ids(self.id, community_id)
        if list_item is None:
            return False
        self.communities.remove(list_item)
        return True


class CommunityListItem(Base):
    __tablename__ = "community_lists"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("communities_users.id"))
    position = Column(Integer)

    community_id = Column(Integer, ForeignKey("community.id"), nullable=False)
    community = relationship("Community")

    @classmethod
    def find_by_ids(
        cls,
        user_id: int,
        community_id: int,
    ) -> CommunityListItem | None:
        return db.session.get_first(
            select(cls).filter_by(user_id=user_id, community_id=community_id)
        )
