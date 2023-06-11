from __future__ import annotations

from typing import Self

from flask_fullstack import PydanticModel
from sqlalchemy import Column, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import Integer

from common import User
from common.abstract import SoftDeletable
from communities.base.meta_db import Community, Participant
from vault import File


class CommunitiesUser(SoftDeletable):
    __tablename__ = "communities_users"

    id: int | Column = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"),
        primary_key=True,
    )
    user = relationship("User", foreign_keys=[id])

    avatar_id = Column(
        Integer,
        ForeignKey("files.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
    )
    avatar = relationship("File", foreign_keys=[avatar_id])

    communities = relationship("Participant", passive_deletes=True)

    @PydanticModel.include_flat_nest_model(User.MainData, "user")
    @PydanticModel.include_nest_model(File.FullModel, "avatar")
    class FullModel(PydanticModel):
        communities: list[Community.IndexModel]

        @classmethod
        def callback_convert(
            cls, callback, orm_object: CommunitiesUser, **context
        ) -> None:
            callback(
                communities=[
                    Community.IndexModel.convert(community, **context)
                    for community in Participant.get_communities_list(orm_object.id)
                ]
            )

    class TempModel(FullModel):
        a: str = "Success"

    @classmethod
    def _create_empty(cls, user_id: int) -> Self:
        return cls.create(id=user_id)

    @classmethod
    def find_by_id(cls, user_id: int) -> Self | None:
        return cls.find_first_not_deleted(id=user_id)

    @classmethod
    def find_or_create(cls, user_id: int) -> Self:
        return cls.find_by_id(user_id) or cls._create_empty(user_id)

    def reorder_community_list(
        self,
        source_id: int,
        target_index: int | None,
    ) -> bool:
        list_item = Participant.find_by_ids(source_id, self.id)
        if list_item is None:  # TODO pragma: no coverage
            return False
        list_item.move(target_index)
        return True

    def leave_community(self, community_id: int) -> bool:
        list_item = Participant.find_by_ids(community_id, self.id)
        if list_item is None:  # TODO pragma: no coverage
            return False
        list_item.delete()
        return True
