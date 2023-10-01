from __future__ import annotations

from flask_fullstack import DuplexEvent, EventSpace
from flask_socketio import join_room, leave_room
from pydantic.v1 import BaseModel, Field

from common import EventController
from communities.base.meta_db import Community, Participant
from communities.base.roles_db import ParticipantRole, PermissionType
from communities.base.utils import check_permission, check_participant
from users.users_db import User

controller = EventController()


@controller.route()
class ParticipantsEventSpace(EventSpace):
    class CommunityIdModel(BaseModel):
        community_id: int

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
    @controller.database_searcher(Participant)
    @check_permission(controller, PermissionType.MANAGE_PARTICIPANTS)
    @controller.marshal_ack(Participant.FullModel)
    def update_participant(
        self,
        event: DuplexEvent,
        participant: Participant,
        community: Community,
        role_ids: list[int],
    ):
        current_role_ids: set[int] = set(
            ParticipantRole.get_role_ids(participant_id=participant.id)
        )

        received_role_ids: set[int] = set(role_ids)

        ParticipantRole.delete_by_ids(
            participant_id=participant.id,
            role_ids=current_role_ids - received_role_ids,
        )

        ParticipantRole.create_bulk(
            participant_id=participant.id, role_ids=received_role_ids - current_role_ids
        )
        event.emit_convert(participant, self.room_name(community.id))
        return participant

    class DeleteModel(CommunityIdModel):
        participant_id: int

    @controller.argument_parser(DeleteModel)
    @controller.mark_duplex(use_event=True)
    @controller.database_searcher(Participant)
    @check_permission(controller, PermissionType.MANAGE_PARTICIPANTS, use_user=True)
    @controller.force_ack()
    def delete_participant(
        self,
        event: DuplexEvent,
        participant: Participant,
        user: User,
        community: Community,
    ):
        if participant.user_id == user.id:
            controller.abort(400, "Target is the source")
        participant.delete()
        event.emit_convert(
            room=self.room_name(community.id),
            participant_id=participant.id,
            community_id=community.id,
        )
