from __future__ import annotations

from flask_fullstack import DuplexEvent, EventSpace
from pydantic import BaseModel, Field

from common import EventController, User
from communities.base.meta_db import Community, ParticipantRole
from communities.base.users_ext_db import CommunitiesUser
from communities.utils import check_participant

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
        CommunitiesUser.find_or_create(user.id)
        community = Community.create(name, user.id, description)
        event.emit_convert(community, user_id=user.id)
        return community

    class CommunityIdModel(BaseModel):
        community_id: int

    @controller.argument_parser(CommunityIdModel)
    @controller.mark_duplex(use_event=True)
    @check_participant(controller, use_user=True)
    @controller.force_ack()
    def leave_community(self, event: DuplexEvent, user: User, community: Community):
        cu = CommunitiesUser.find_or_create(user.id)
        cu.leave_community(community.id)
        event.emit_convert(user_id=user.id, community_id=community.id)

    class ReorderModel(BaseModel):
        community_id: int = Field(alias="source-id")
        target_index: int = None

    @controller.argument_parser(ReorderModel)
    @controller.mark_duplex(use_event=True)
    @check_participant(controller, use_user=True)
    def reorder_community(
        self,
        event: DuplexEvent,
        user: User,
        community: Community,
        target_index: int | None,
    ):
        cu = CommunitiesUser.find_or_create(user.id)
        if not cu.reorder_community_list(community.id, target_index):
            controller.abort(
                404, "Community not in the list"
            )  # TODO pragma: no coverage
        event.emit_convert(
            user_id=user.id,
            community_id=community.id,
            target_index=target_index,
        )

    class UpdateModel(Community.CreateModel, CommunityIdModel):
        pass

    @controller.argument_parser(UpdateModel)
    @controller.mark_duplex(Community.IndexModel, use_event=True)
    @check_participant(controller, role=ParticipantRole.OWNER, use_user=True)
    @controller.marshal_ack(Community.IndexModel)
    def update_community(
        self,
        event: DuplexEvent,
        user: User,
        community: Community,
        name: str = None,
        description: str = None,
    ):
        if name is not None:
            community.name = name
        if description is not None:
            community.description = description
        event.emit_convert(community, user_id=user.id, community_id=community.id)
        return community

    @controller.argument_parser(CommunityIdModel)
    @controller.mark_duplex(use_event=True)
    @check_participant(controller, role=ParticipantRole.OWNER, use_user=True)
    @controller.force_ack()
    def delete_community(
        self,
        event: DuplexEvent,
        community: Community,
        user: User,
    ):
        community.deleted = True
        event.emit_convert(user_id=user.id, community_id=community.id)
