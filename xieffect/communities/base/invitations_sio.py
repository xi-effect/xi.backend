from __future__ import annotations

from pydantic import BaseModel, Field

from common import EventController, EventSpace, ServerEvent, DuplexEvent, User
from .invitations_db import Invitation
from .meta_db import Community, Participant, ParticipantRole

controller = EventController()


@controller.route()
class InvitationsEventSpace(EventSpace):
    class CreationModel(Invitation.CreationBaseModel):
        community_id: int
        days: int = None

    @controller.doc_abort(400, "Invalid role")
    @controller.doc_abort(403, "Permission Denied")
    @controller.argument_parser(CreationModel)
    @controller.mark_duplex(Invitation.IndexModel, use_event=True)
    @controller.jwt_authorizer(User)
    @controller.database_searcher(Community, use_session=True)
    @controller.marshal_ack(Invitation.IndexModel)
    def new_invite(self, event: DuplexEvent, session, user: User, community: Community,
                   role: str, limit: int | None, days: int | None):
        enum_role: ParticipantRole = ParticipantRole.from_string(role)
        if enum_role is None:
            controller.abort(400, f"Invalid role: {role}")

        participant = Participant.find_by_ids(session, community.id, user.id)
        if participant is None:
            controller.abort(403, "Permission Denied: Participant not found")

        if participant.role.value < ParticipantRole.OWNER.value:
            controller.abort(403, "Permission Denied: Low role")

        invitation = Invitation.create(session, community.id, enum_role, limit, days)
        event.emit_convert(invitation, f"cs-invites-{community.id}")
        return invitation
