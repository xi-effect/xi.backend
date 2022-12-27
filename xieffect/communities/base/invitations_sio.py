from __future__ import annotations

from flask_fullstack import EventSpace, DuplexEvent
from flask_socketio import join_room, leave_room
from pydantic import BaseModel

from common import EventController
from .invitations_db import Invitation
from .meta_db import Community
from .roles_db import PermissionType
from ..utils import check_participant

controller = EventController()


@controller.route()
class InvitationsEventSpace(EventSpace):
    @classmethod  # TODO fix in ffs
    def room_name(cls, community_id: int):
        return f"cs-invites-{community_id}"

    class CommunityIdModel(BaseModel):
        community_id: int

    @controller.argument_parser(CommunityIdModel)
    @check_participant(controller, permission=PermissionType.MANAGE_INVITATIONS)
    @controller.force_ack()
    def open_invites(self, community: Community):
        join_room(self.room_name(community.id))

    @controller.argument_parser(CommunityIdModel)
    @check_participant(controller, permission=PermissionType.MANAGE_INVITATIONS)
    @controller.force_ack()
    def close_invites(self, community: Community):
        leave_room(self.room_name(community.id))

    class CreationModel(Invitation.CreationBaseModel, CommunityIdModel):
        days: int = None

    @controller.doc_abort(400, "Invalid role")
    @controller.argument_parser(CreationModel)
    @controller.mark_duplex(Invitation.IndexModel, use_event=True)
    @check_participant(controller, permission=PermissionType.MANAGE_INVITATIONS)
    @controller.marshal_ack(Invitation.IndexModel)
    def new_invite(
        self,
        event: DuplexEvent,
        community: Community,
        limit: int | None,
        days: int | None,
    ):
        invitation = Invitation.create(community.id, limit, days)
        event.emit_convert(invitation, self.room_name(community.id))
        return invitation

    class InvitationIdsModel(CommunityIdModel):
        invitation_id: int

    @controller.argument_parser(InvitationIdsModel)
    @controller.mark_duplex(InvitationIdsModel, use_event=True)
    @check_participant(controller, permission=PermissionType.MANAGE_INVITATIONS)
    @controller.database_searcher(Invitation)
    @controller.force_ack()
    def delete_invite(
        self, event: DuplexEvent, community: Community, invitation: Invitation
    ):
        invitation.delete()
        event.emit_convert(
            room=self.room_name(community_id=community.id),
            community_id=community.id,
            invitation_id=invitation.id,
        )
