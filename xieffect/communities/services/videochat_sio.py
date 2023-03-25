from __future__ import annotations

from flask_fullstack import DuplexEvent, EventSpace
from flask_socketio import join_room, leave_room
from pydantic import BaseModel

from common import EventController, User
from .videochat_db import ChatMessage, ChatParticipant, PARTICIPANT_LIMIT
from ..base import Community
from ..utils import check_participant, ParticipantRole, Participant

controller = EventController()


@controller.route()
class VideochatEventSpace(EventSpace):
    @classmethod
    def room_name(cls, community_id: int) -> str:
        return f"cs-videochat-{community_id}"

    class CommunityIdModel(BaseModel):
        community_id: int

    @controller.doc_abort(413, "Too many participants")
    @controller.argument_parser(ChatParticipant.CreateModel)
    @controller.mark_duplex(ChatParticipant.IndexModel, use_event=True)
    @check_participant(controller, use_user=True)
    @controller.marshal_ack(ChatParticipant.IndexModel)
    def new_participant(
        self,
        event: DuplexEvent,
        user: User,
        community: Community,
        state: dict,
    ):
        participant_count = ChatParticipant.get_count_by_community(community.id)
        if participant_count >= PARTICIPANT_LIMIT:  # TODO pragma: no cover
            controller.abort(413, "Too many participants")
        participant = ChatParticipant.create(user.id, community.id, state)
        join_room(self.room_name(community.id))
        event.emit_convert(participant, self.room_name(community.id))
        return participant

    class DeleteParticipant(CommunityIdModel):
        participant_id: int

    @controller.doc_abort(404, "Participant not found")
    @controller.argument_parser(DeleteParticipant)
    @controller.mark_duplex(DeleteParticipant, use_event=True)
    @check_participant(controller)
    @controller.force_ack()
    def delete_participant(
        self, event: DuplexEvent, participant_id: int, community: Community
    ):
        participant = ChatParticipant.find_by_ids(participant_id, community.id)
        if participant is None:
            controller.abort(404, "Participant not found")
        participant.delete()
        event.emit_convert(
            room=self.room_name(community_id=community.id),
            participant_id=participant_id,
            community_id=community.id,
        )
        leave_room(self.room_name(community.id))

    class CreateModel(ChatMessage.CreateModel, CommunityIdModel):
        pass

    @controller.argument_parser(CreateModel)
    @controller.mark_duplex(ChatMessage.IndexModel, use_event=True)
    @check_participant(controller, use_user=True)
    @controller.marshal_ack(ChatMessage.IndexModel)
    def send_message(
        self, event: DuplexEvent, content: str, user: User, community: Community
    ):
        message = ChatMessage.create(user, community.id, content)
        event.emit_convert(message, self.room_name(community.id))
        return message

    class DeleteMessage(CommunityIdModel):
        message_id: int

    @controller.doc_abort(403, "Permission Denied")
    @controller.argument_parser(DeleteMessage)
    @controller.mark_duplex(DeleteMessage, use_event=True)
    @check_participant(controller, use_participant=True)
    @controller.database_searcher(
        ChatMessage, input_field_name="message_id", result_field_name="message"
    )
    @controller.force_ack()
    def delete_message(
        self,
        event: DuplexEvent,
        community: Community,
        message: ChatMessage,
        participant: Participant,
    ):
        checks = [
            participant.user_id == message.sender_id,
            participant.role == ParticipantRole.OWNER,
        ]
        if not any(checks):
            controller.abort(403, "Permission Denied")
        message.delete()
        event.emit_convert(
            room=self.room_name(community_id=community.id),
            community_id=community.id,
            message_id=message.id,
        )

    class StateModel(CommunityIdModel):
        target: str
        state: bool

    @controller.argument_parser(StateModel)
    @controller.mark_duplex(ChatParticipant.IndexModel, use_event=True)
    @check_participant(controller, use_user=True)
    @controller.marshal_ack(ChatParticipant.IndexModel)
    def change_state(
        self,
        event: DuplexEvent,
        target: str,
        state: bool,
        user: User,
        community: Community,
    ):
        participant = ChatParticipant.find_by_ids(user.id, community.id)
        participant.state[target] = state
        event.emit_convert(participant, self.room_name(community.id))
        return participant

    class ActionModel(CommunityIdModel):
        participant_id: int
        action_type: str
        action: str

    @controller.argument_parser(ActionModel)
    @controller.mark_duplex(use_event=True)
    @check_participant(controller)
    def send_action(
        self,
        event: DuplexEvent,
        action_type: str,
        action: str,
        participant_id: int,
        community: Community,
    ):
        event.emit_convert(
            room=self.room_name(community.id),
            community_id=community.id,
            participant_id=participant_id,
            action_type=action_type,
            action=action,
        )
