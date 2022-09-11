from __future__ import annotations

from pydantic import BaseModel, Field

from common import DuplexEvent, EventController, EventSpace, User, db
from .meta_db import Community
from .users_ext_db import CommunitiesUser

controller = EventController()


@controller.route()
class CommunitiesEventSpace(EventSpace):
    @controller.argument_parser(Community.CreateModel)
    @controller.mark_duplex(Community.IndexModel, use_event=True)
    @controller.jwt_authorizer(User)
    @controller.marshal_ack(Community.IndexModel, force_wrap=True)
    def new_community(
        self,
        event: DuplexEvent,
        user: User,
        name: str,
        description: str = None,
    ):
        community = Community.create(name, description, user)
        cu = CommunitiesUser.find_or_create(user.id)
        cu.join_community(community.id)
        db.session.commit()  # TODO move inside controller's logic!

        event.emit_convert(community, user_id=user.id)
        return community

    class CommunityIdModel(BaseModel):
        community_id: int

    @controller.argument_parser(CommunityIdModel)
    @controller.mark_duplex(use_event=True)
    @controller.jwt_authorizer(User)
    @controller.database_searcher(Community)
    @controller.force_ack()
    def leave_community(self, event: DuplexEvent, user: User, community: Community):
        cu = CommunitiesUser.find_or_create(user.id)
        cu.leave_community(community.id)
        db.session.commit()  # TODO move inside controller's logic!
        event.emit_convert(user_id=user.id, community_id=community.id)

    class ReorderModel(BaseModel):
        community_id: int = Field(alias="source-id")
        target_index: int

    @controller.argument_parser(ReorderModel)
    @controller.mark_duplex(use_event=True)
    @controller.jwt_authorizer(User)
    @controller.database_searcher(Community)
    def reorder_community(
        self,
        event: DuplexEvent,
        user: User,
        community: Community,
        target_index: int,
    ):
        cu = CommunitiesUser.find_or_create(user.id)
        if not cu.reorder_community_list(community.id, target_index):
            controller.abort(404, "Community not in the list")

        db.session.commit()  # TODO move inside controller's logic!
        event.emit_convert(
            user_id=user.id,
            community_id=community.id,
            target_index=target_index,
        )
