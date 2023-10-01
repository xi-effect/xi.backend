from __future__ import annotations

from flask_fullstack import DuplexEvent, EventSpace
from flask_fullstack.restx.marshals import v2_model_to_ffs
from flask_socketio import join_room, leave_room
from pydantic.v1 import BaseModel, Field

from common import EventController
from communities.base.meta_db import Community, Participant
from communities.base.roles_db import PermissionType
from communities.base.utils import check_participant, check_permission
from users.users_db import User
from vault.files_db import File

controller = EventController()


@controller.route()
class CommunitiesEventSpace(EventSpace):
    @classmethod
    def room_name(cls, community_id: int) -> str:
        return f"community-{community_id}"

    class CommunityIdModel(BaseModel):
        community_id: int

    @controller.argument_parser(CommunityIdModel)
    @check_participant(controller)
    @controller.force_ack()
    def open_communities(self, community: Community):
        join_room(self.room_name(community_id=community.id))

    @controller.argument_parser(CommunityIdModel)
    @check_participant(controller)
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
        community = Community.create(name, user.id, description)
        event.emit_convert(community, user_id=user.id)
        return community

    @controller.argument_parser(CommunityIdModel)
    @controller.mark_duplex(use_event=True)
    @check_participant(controller, use_participant=True)
    @controller.force_ack()
    def leave_community(
        self, event: DuplexEvent, participant: Participant, community: Community
    ):
        participant.delete()
        event.emit_convert(user_id=participant.user_id, community_id=community.id)

    class ReorderModel(BaseModel):
        community_id: int = Field(alias="source-id")
        target_index: int = None

    @controller.argument_parser(ReorderModel)
    @controller.mark_duplex(use_event=True)
    @check_participant(controller, use_participant=True)
    def reorder_community(
        self,
        event: DuplexEvent,
        participant: Participant,
        community: Community,
        target_index: int | None,
    ):
        participant.move(target_index)
        event.emit_convert(
            user_id=participant.user_id,
            community_id=community.id,
            target_index=target_index,
        )

    class UpdateModel(
        CommunityIdModel,
        v2_model_to_ffs(Community.CreateModel),  # noqa: WPS606
    ):
        avatar_id: int | None = -1  # TODO [nq] fix in ffs!

    @controller.argument_parser(UpdateModel)
    @controller.mark_duplex(Community.IndexModel, use_event=True)
    @check_permission(controller, PermissionType.MANAGE_COMMUNITY)
    @controller.marshal_ack(Community.IndexModel)
    def update_community(
        self,
        event: DuplexEvent,
        community: Community,
        avatar_id: int | None,
        name: str = None,
        description: str = None,
    ):
        if name is not None:
            community.name = name
        if description is not None:
            community.description = description

        if avatar_id is None:
            community.avatar.delete()
            community.avatar = None
        elif avatar_id != -1:  # TODO [nq] fix in ffs!
            new_file = File.find_by_id(avatar_id)
            if new_file is None:
                controller.abort(404, File.not_found_text)
            if community.avatar is not None:
                community.avatar.delete()
            community.avatar = new_file

        event.emit_convert(
            community,
            room=self.room_name(community_id=community.id),
            community_id=community.id,
        )
        return community

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
