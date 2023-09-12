from __future__ import annotations

from flask_fullstack import DuplexEvent, EventSpace
from flask_socketio import join_room, leave_room
from pydantic import BaseModel, Field

from common import EventController, User
from communities.base.meta_db import Community
from communities.base.roles_db import PermissionType
from communities.base.users_ext_db import CommunitiesUser
from communities.base.utils import check_participant, check_permission
from vault import File

controller = EventController()


@controller.route()
class CommunitiesEventSpace(EventSpace):
    @classmethod
    def room_name(cls, community_id: int) -> str:
        return f"community-{community_id}"

    class CommunityIdModel(BaseModel):
        community_id: int

    @controller.argument_parser(CommunityIdModel)
    @check_permission(controller, PermissionType.MANAGE_COMMUNITY)
    @controller.force_ack()
    def open_communities(self, community: Community):
        join_room(self.room_name(community_id=community.id))

    @controller.argument_parser(CommunityIdModel)
    @check_permission(controller, PermissionType.MANAGE_COMMUNITY)
    @controller.force_ack()
    def close_communities(self, community: Community):
        leave_room(self.room_name(community_id=community.id))

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

    @controller.argument_parser(Community.IndexModel)
    @controller.mark_duplex(Community.IndexModel, use_event=True)
    @check_permission(controller, PermissionType.MANAGE_COMMUNITY)
    @controller.database_searcher(File, input_field_name="avatar_id", check_only=True)
    @controller.marshal_ack(Community.IndexModel)
    def update_community(
        self,
        event: DuplexEvent,
        community: Community,
        name: str = None,
        description: str = None,
        file: File = None,
    ):
        if name is not None:
            community.name = name
        if description is not None:
            community.description = description
        if file is not None:
            community.avatar_id = file.id
        event.emit_convert(
            community,
            room=self.room_name(community_id=community.id),
            community_id=community.id,
        )
        return community

    @controller.argument_parser(CommunityIdModel)
    @controller.mark_duplex(Community.IndexModel, use_event=True)
    @check_permission(controller, PermissionType.MANAGE_COMMUNITY)
    @controller.database_searcher(Community)
    @controller.force_ack()
    def delete_avatar(self, event: DuplexEvent, community: Community):
        community.avatar.delete()
        event.emit_convert(
            community,
            room=self.room_name(community_id=community.id),
            community_id=community.id,
        )

    @controller.argument_parser(CommunityIdModel)
    @controller.mark_duplex(use_event=True)
    @check_permission(controller, PermissionType.MANAGE_COMMUNITY, use_user=True)
    @controller.force_ack()
    def delete_community(
        self,
        event: DuplexEvent,
        community: Community,
        user: User,
    ):
        community.soft_delete()
        event.emit_convert(user_id=user.id, community_id=community.id)
