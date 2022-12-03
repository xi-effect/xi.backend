from __future__ import annotations

from flask_fullstack import DuplexEvent, EventSpace
from flask_socketio import join_room, leave_room
from pydantic import BaseModel

from common import EventController, User, db
from .videochat_db import CommunityMessage, CommunityParticipant, PARTICIPANT_LIMIT
from ..base import Community
from ..utils import check_participant

controller = EventController()


@controller.route()
class VideochatEventSpace(EventSpace):
    @classmethod
    def room_name(cls, community_id: int):
        return f"cs-videochat-{community_id}"

    class CommunityIdModel(BaseModel):
        community_id: int

    @controller.argument_parser(CommunityIdModel)
    @check_participant(controller)
    @controller.force_ack()
    def open_videochat(self, community: Community):
        join_room(self.room_name(community.id))

    @controller.argument_parser(CommunityIdModel)
    @check_participant(controller)
    @controller.force_ack()
    def close_videochat(self, community: Community):
        leave_room(self.room_name(community.id))

    @controller.argument_parser(CommunityParticipant.CreateModel)
    @controller.mark_duplex(CommunityParticipant.IndexModel, use_event=True)
    @check_participant(controller, use_user=True)
    @controller.marshal_ack(CommunityParticipant.IndexModel)
    def new_participant(
        self,
        event: DuplexEvent,
        user: User,
        community: Community,
    ):
        participant_list = CommunityParticipant.find_by_community(community.id)
        if len(participant_list) == PARTICIPANT_LIMIT:
            controller.abort(403, "Too much participants")
        participant = CommunityParticipant.create(user.id, community.id)
        db.session.commit()
        event.emit_convert(participant, self.room_name(community.id))
        return participant

    class DeleteModel(CommunityIdModel):
        participant_id: int

    @controller.argument_parser(CommunityIdModel)
    @controller.mark_duplex(CommunityIdModel)
    @check_participant(controller)
    @controller.force_ack()
    def delete_participant(
        self, event: DuplexEvent, participant_id: int, community: Community
    ):
        participant = CommunityParticipant.find_by_ids(participant_id, community.id)
        participant.delete()
        db.session.commit()
        event.emit_convert(
            room=self.room_name(community_id=community.id),
            community_id=community.id,
            participant_id=participant.id
        )

    class SendModel(CommunityMessage.TextModel, CommunityIdModel):
        pass

    @controller.argument_parser(SendModel)
    @controller.mark_duplex(CommunityMessage.IndexModel, use_event=True)
    @check_participant(controller, use_user=True)
    @controller.marshal_ack(CommunityMessage.IndexModel)
    def send_message(
        self, event: DuplexEvent, text: str, user: User, community: Community
    ):
        message = CommunityMessage.create(user, community.id, text)
        db.session.commit()
        event.emit_convert(message, self.room_name(community.id))
        return message

    class DeviceModel(CommunityIdModel):
        target: str
        state: bool

    @controller.argument_parser(DeviceModel)
    @controller.mark_duplex(CommunityParticipant.IndexModel, use_event=True)
    @check_participant(controller, use_user=True)
    @controller.marshal_ack(CommunityParticipant.IndexModel)
    def device_status(
        self,
        event: DuplexEvent,
        target: str,
        state: bool,
        user: User,
        community: Community,
    ):
        participant = CommunityParticipant.find_by_ids(user.id, community.id)
        if participant.get_by_string(target) is None:
            controller.abort(404, "Device not found")
        participant.set_by_string(target, state)
        db.session.commit()
        event.emit_convert(participant, self.room_name(community.id))
        return participant

    class ReactionModel(CommunityIdModel):
        action_type: str
        action: str

    @controller.argument_parser(ReactionModel)
    @controller.mark_duplex(use_event=True)
    @check_participant(controller, use_user=True)
    def send_reaction(
        self,
        event: DuplexEvent,
        action_type: str,
        action: str,
        user: User,
        community: Community,
    ):
        event.emit_convert(
            room=self.room_name(community.id),
            user_id=user.id,
            action_type=action_type,
            action=action,
        )
