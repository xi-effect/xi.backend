from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import Column, ForeignKey, select
from sqlalchemy.ext.orderinglist import ordering_list
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import Integer

from common import PydanticModel, Base, sessionmaker, User
from communities.base.meta_db import Community


class CommunitiesUser(Base):
    __tablename__ = "communities_users"

    id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    user = relationship("User")

    communities = relationship("CommunityListItem", order_by="CommunityListItem.position",
                               collection_class=ordering_list("position"))

    FullModel = PydanticModel.nest_model(User.MainData, "user").nest_model(Community.IndexModel, "communities")

    # @PydanticModel.include_nest_model(User.MainData, "user")
    # class FullModel(PydanticModel):
    #     communities: list[Community.IndexModel]
#
    #     @classmethod
    #     def callback_convert(cls, callback: Callable, orm_object: CommunitiesUser, **context) -> None:
    #         callback(communities=[Community.IndexModel.convert(ci.community, **context)
    #                               for ci in orm_object.communities])

    @classmethod
    def _create_empty(cls, session, user_id: int) -> CommunitiesUser:
        return cls.create(session, id=user_id)

    @classmethod
    def find_by_id(cls, session: sessionmaker, user_id: int) -> CommunitiesUser | None:
        return session.get_first(select(cls).filter_by(id=user_id))

    @classmethod
    def find_or_create(cls, session: sessionmaker, user_id: int) -> CommunitiesUser:
        return cls.find_by_id(session, user_id) or cls._create_empty(session, user_id)

    def reorder_community_list(self, session, source_id: int, target_index: int) -> bool:
        list_item = CommunityListItem.find_by_community(session, source_id)
        if list_item is None:
            return False
        self.communities.remove(list_item)
        self.communities.insert(target_index, list_item)
        return True

    def join_community(self, community_id: int) -> None:  # autocommit  # TODO find a way to reverse the list
        new_item = CommunityListItem(community_id=community_id)
        self.communities.insert(0, new_item)

    def leave_community(self, session, community_id: int) -> bool:
        list_item = CommunityListItem.find_by_community(session, community_id)
        if list_item is None:
            return False
        self.communities.remove(list_item)
        return True


class CommunityListItem(Base):
    __tablename__ = "community_lists"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("communities_users.id"))
    position = Column(Integer)

    community_id = Column(Integer, ForeignKey("community.id"), nullable=False, unique=True)
    community = relationship("Community")

    @classmethod
    def find_by_community(cls, session, community_id: int) -> CommunityListItem | None:
        return session.get_first(select(cls).filter_by(id=community_id))
