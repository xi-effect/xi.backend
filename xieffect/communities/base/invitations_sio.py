from __future__ import annotations

from functools import wraps

from flask_socketio import join_room, leave_room
from pydantic import BaseModel

from common import EventController, EventSpace, DuplexEvent, User, get_or_pop
from .invitations_db import Invitation
from .meta_db import Community, Participant, ParticipantRole

controller = EventController()


def check_participant_role(role: ParticipantRole, use_session: bool = True, use_user: bool = False,
                           use_participant: bool = False, use_community: bool = True):
    def check_participant_role_wrapper(function):
        @wraps(function)
        @controller.doc_abort(403, "Permission Denied")
        @controller.jwt_authorizer(User)
        @controller.database_searcher(Community, use_session=True)
        def check_participant_role_inner(*args, **kwargs):
            session = get_or_pop(kwargs, "session", use_session)
            user = get_or_pop(kwargs, "user", use_user)
            community = get_or_pop(kwargs, "community", use_community)

            participant = Participant.find_by_ids(session, community.id, user.id)
            if participant is None:
                controller.abort(403, "Permission Denied: Participant not found")

            if participant.role.value < role.value:
                controller.abort(403, "Permission Denied: Low role")

            if use_participant:
                kwargs["participant"] = participant

            return function(*args, **kwargs)

        return check_participant_role_inner

    return check_participant_role_wrapper


@controller.route()
class InvitationsEventSpace(EventSpace):
    @classmethod  # TODO fix in ffs
    def room_name(cls, community_id: int):
        return f"cs-invites-{community_id}"

    class CommunityIdModel(BaseModel):
        community_id: int

    @controller.argument_parser(CommunityIdModel)
    @check_participant_role(ParticipantRole.OWNER, use_session=False)
    @controller.force_ack()
    def open_invites(self, community: Community):
        join_room(self.room_name(community.id))

    @controller.argument_parser(CommunityIdModel)
    @check_participant_role(ParticipantRole.OWNER, use_session=False)
    @controller.force_ack()
    def close_invites(self, community: Community):
        leave_room(self.room_name(community.id))

    class CreationModel(Invitation.CreationBaseModel, CommunityIdModel):
        days: int = None

    @controller.doc_abort(400, "Invalid role")
    @controller.argument_parser(CreationModel)
    @controller.mark_duplex(Invitation.IndexModel, use_event=True)
    @check_participant_role(ParticipantRole.OWNER)
    @controller.marshal_ack(Invitation.IndexModel)
    def new_invite(self, event: DuplexEvent, session, community: Community,
                   role: str, limit: int | None, days: int | None):
        enum_role: ParticipantRole = ParticipantRole.from_string(role)
        if enum_role is None:
            controller.abort(400, f"Invalid role: {role}")

        invitation = Invitation.create(session, community.id, enum_role, limit, days)
        event.emit_convert(invitation, self.room_name(community.id))
        return invitation

    class InvitationIdsModel(CommunityIdModel):
        invitation_id: int

    @controller.argument_parser(InvitationIdsModel)
    @controller.mark_duplex(InvitationIdsModel, use_event=True)
    @check_participant_role(ParticipantRole.OWNER)
    @controller.database_searcher(Invitation, use_session=True)
    @controller.force_ack()
    def delete_invite(self, event: DuplexEvent, session, community: Community, invitation: Invitation):
        invitation.delete(session)
        event.emit_convert(room=self.room_name(community_id=community.id),
                           community_id=community.id, invitation_id=invitation.id)
