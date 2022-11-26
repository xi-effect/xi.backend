from __future__ import annotations

from flask_fullstack import EventSpace, DuplexEvent
from flask_socketio import leave_room, join_room
from pydantic import BaseModel
from common import EventController
from .meta_db import Community, ParticipantRole
from ..utils import check_participant
from .role_db import Role, RolePermission, PermissionTypes, LimitingQuantityRoles

controller = EventController()


@controller.route()
class RolesEventSpace(EventSpace):
    @classmethod
    def room_name(cls, community_id: int):
        return f"cs-roles-{community_id}"

    class CommunityIdModel(BaseModel):
        community_id: int

    @controller.argument_parser(CommunityIdModel)
    @check_participant(controller)
    @controller.force_ack()
    def open_roles(self, community: Community):
        join_room(self.room_name(community.id))

    @controller.argument_parser(CommunityIdModel)
    @check_participant(controller)
    @controller.force_ack()
    def close_roles(self, community: Community):
        leave_room(self.room_name(community.id))

    class CreateModel(Role.CreateModel, CommunityIdModel):
        permissions: list[str]

    @controller.argument_parser(CreateModel)
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

        if Role.get_count_by_community(community.id) > LimitingQuantityRoles:
            return controller.abort(400, "quantity exceeded")
        role = Role.create(name=name, color=color, community_id=community.id)

        for permission in permissions:
            RolePermission.create(
                role_id=role.id,
                permission_type=PermissionTypes.from_string(permission),
            )

        event.emit_convert(role, self.room_name(community.id))
        return role
