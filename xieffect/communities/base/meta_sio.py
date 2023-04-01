from __future__ import annotations

from flask_fullstack import DuplexEvent, EventSpace
from flask_socketio import join_room, leave_room
from pydantic import BaseModel, Field

from common import EventController, User
from .meta_db import Community, Participant
from .roles_db import ParticipantRole, PermissionType
from .users_ext_db import CommunitiesUser
from .utils import check_permission, check_participant

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
        if not cu.reorder_community_list(community.id, target_index):  # TODO pragma: no coverage
            controller.abort(404, "Community not in the list")
        event.emit_convert(
            user_id=user.id,
            community_id=community.id,
            target_index=target_index,
        )

    @classmethod
    def room_name(cls, community_id: int):
        return f"cs-participants-{community_id}"

    @controller.argument_parser(CommunityIdModel)
    @check_participant(controller)
    @controller.force_ack()
    def open_participants(self, community: Community):
        join_room(self.room_name(community.id))

    @controller.argument_parser(CommunityIdModel)
    @check_participant(controller)
    @controller.force_ack()
    def close_participants(self, community: Community):
        leave_room(self.room_name(community.id))

    class UpdateModel(CommunityIdModel):
        role_ids: list[int] = Field(default_factory=list)
        participant_id: int

    @controller.argument_parser(UpdateModel)
    @controller.mark_duplex(Participant.FullModel, use_event=True)
    @check_permission(controller, PermissionType.MANAGE_PARTICIPANT, use_participant=True)
    @controller.marshal_ack(Participant.FullModel)
    def update_participant_role(
        self,
        event: DuplexEvent,
        participant: Participant,
        community: Community,
        role_ids: list[int],
    ):
        role_ids_from_db = set(
            ParticipantRole.get_role_ids(participant_id=participant.id)
        )

        received_role_ids = set(role_ids)

        for role_id in role_ids_from_db - received_role_ids:
            ParticipantRole.delete_by_participant(
                participant_id=participant.id,
                role_id=role_id,
            )

        ParticipantRole.create_bulk(
            participant_id=participant.id, role_ids=received_role_ids - role_ids_from_db
        )
        event.emit_convert(participant, self.room_name(community.id))
        return participant

    class DeleteModel(CommunityIdModel):
        participant_id: int

    @controller.argument_parser(DeleteModel)
    @controller.mark_duplex(use_event=True)
    @controller.database_searcher(Participant)
    @check_permission(controller, PermissionType.MANAGE_PARTICIPANT, use_user=True)
    @controller.force_ack()
    def delete_participant_role(
        self, event: DuplexEvent, participant: Participant, user: User, community: Community
    ):
        if participant.user_id == user.id:
            controller.abort(400, "Forbidden remove yourself")
        participant.delete()
        event.emit_convert(
            room=self.room_name(community.id),
            participant_id=participant.id,
            community_id=community.id,
        )
