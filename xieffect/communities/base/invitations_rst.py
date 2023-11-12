from __future__ import annotations

from functools import wraps

from flask_fullstack import PydanticModel, counter_parser
from flask_fullstack.restx.marshals import v2_model_to_ffs
from flask_restx import Resource

from common import ResourceController
from communities.base.invitations_db import Invitation
from communities.base.meta_db import Community, Participant
from communities.base.meta_sio import CommunitiesEventSpace
from communities.base.roles_db import PermissionType, ParticipantRole
from communities.base.utils import check_permission
from users.users_db import User

controller = ResourceController("communities-invitation", path="/communities/")
INVITATIONS_PER_REQUEST = 20


@controller.route("/<int:community_id>/invitations/")
class InvitationLister(Resource):
    @check_permission(controller, PermissionType.MANAGE_INVITATIONS)
    @controller.argument_parser(counter_parser)
    @controller.lister(INVITATIONS_PER_REQUEST, Invitation.FullModel)
    def get(self, community: Community, start: int, finish: int):
        return Invitation.find_by_community(community.id, start, finish - start)


@controller.route("/<int:community_id>/invitations/index/")
class OldInvitationLister(Resource):  # pragma: no coverage
    @check_permission(controller, PermissionType.MANAGE_INVITATIONS)
    @controller.argument_parser(counter_parser)
    @controller.lister(INVITATIONS_PER_REQUEST, Invitation.FullModel)
    def post(self, community: Community, start: int, finish: int):
        return Invitation.find_by_community(community.id, start, finish - start)


def check_invitation():  # TODO # noqa: WPS231
    def check_invitation_wrapper(function):
        @controller.doc_abort("400 ", "Invalid invitation")
        @wraps(function)
        def check_invitation_inner(*args, **kwargs):
            code: str = kwargs.pop("code")
            user: User = kwargs.get("user")

            invitation: Invitation = Invitation.find_by_code(code)
            if invitation is None:
                controller.abort(400, "Invalid invitation")
            if (  # noqa: WPS337
                user is not None
                and Participant.find_by_ids(invitation.community_id, user.id)
                is not None
            ):
                return function(
                    *args, invitation=None, community=invitation.community, **kwargs
                )
            if invitation.is_invalid():
                invitation.delete()
                controller.abort(400, "Invalid invitation")

            return function(
                *args, invitation=invitation, community=invitation.community, **kwargs
            )

        return check_invitation_inner

    return check_invitation_wrapper


CommunityIndexModel = v2_model_to_ffs(Community.IndexModel)


class InvitePreview(PydanticModel):
    joined: bool
    authorized: bool
    community: CommunityIndexModel = None


@controller.route("/join/<code>/")
class InvitationJoin(Resource):
    @controller.proxy_authorizer(optional=True)
    @check_invitation()
    @controller.marshal_with(InvitePreview)
    def get(
        self,
        user_id: int | None,
        invitation: Invitation | None,
        community: Community,
    ) -> InvitePreview:
        return InvitePreview(
            joined=invitation is None,
            authorized=user_id is not None,
            community=CommunityIndexModel.convert(community),
        )

    @controller.doc_abort(400, "User has already joined")
    @controller.proxy_authorizer()
    @check_invitation()
    @controller.marshal_with(Community.IndexModel)
    def post(
        self,
        user_id: int | None,
        invitation: Invitation | None,
        community: Community,
    ) -> Community:
        if invitation is None:
            controller.abort(400, "User has already joined")
        participant = Participant.add(
            community_id=community.id,
            user_id=user_id,
        )
        ParticipantRole.create_bulk(
            participant_id=participant.id,
            role_ids=[role.id for role in invitation.roles],
        )
        if invitation.limit == 1:
            invitation.delete()
        elif invitation.limit is not None:
            invitation.limit -= 1

        CommunitiesEventSpace.new_community.emit_convert(
            community, include_self=True, user_id=user_id
        )

        return community
