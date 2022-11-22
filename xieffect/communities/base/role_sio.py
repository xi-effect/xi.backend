from __future__ import annotations

from flask_fullstack import EventSpace
from flask_socketio import leave_room, join_room

from common import EventController
from .meta_db import Community, ParticipantRole
from ..utils import check_participant

controller = EventController()


@controller.route()
class RolesEventSpace(EventSpace):

    @classmethod
    def room_name(cls, community_id: int):
        return f"cs-roles-{community_id}"

    @controller.argument_parser()
    @controller.force_ack()
    def open_roles(self, community: Community):
        join_room(self.room_name(community.id))

    @controller.argument_parser()
    @controller.force_ack()
    def close_roles(self, community: Community):
        leave_room(self.room_name(community.id))

    @controller.argument_parser()
    @check_participant(controller, role=ParticipantRole.OWNER)
    def new_role(self):
        pass
