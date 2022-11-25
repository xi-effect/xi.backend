from __future__ import annotations

from flask_fullstack import EventSpace, DuplexEvent, TypeEnum as enum
from flask_socketio import leave_room, join_room
from pydantic import BaseModel

from common import EventController
from .meta_db import Community, ParticipantRole
from ..utils import check_participant
from .role_db import Role, RolePermission, LimitingQuantityRoles as limit

controller = EventController()


@controller.route()
class RolesEventSpace(EventSpace):
    @classmethod
    def room_name(cls, community_id: int):
        return f"cs-roles-{community_id}"

    class CommunityIdModel(BaseModel):
        community_id: int

    @controller.argument_parser()
    @controller.force_ack()
    def open_roles(self, community: Community):
        join_room(self.room_name(community.id))

    @controller.argument_parser()
    @controller.force_ack()
    def close_roles(self, community: Community):
        leave_room(self.room_name(community.id))

    @controller.argument_parser()
    @controller.mark_duplex(Role.IndexModel, use_event=True)
    @check_participant(controller, role=ParticipantRole.OWNER)
    @controller.marshal_ack(Role.IndexModel)
    def new_role(
        self,
        event: DuplexEvent,
        name: str,
        color: str,
        permissions: list,
        community: Community,
    ):
        if quantity := Role.get_count(community.id) > limit:
            controller.abort(
                400, f"Quantity exceeded in category now{quantity} must be not more {limit}"
            )
        else:
            role = Role.create(name=name, color=color, community_id=community.id)
            [
                RolePermission.create(
                    role_id=role.id, permission_type=enum.from_string(permission)
                )
                for permission in permissions
            ]
            event.emit_convert(role, self.room_name(community.id))
            return role

