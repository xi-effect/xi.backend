from __future__ import annotations

from functools import wraps

from flask_fullstack import PydanticModel, counter_parser
from flask_restx import Resource

from common import ResourceController, User
from communities.base.invitations_db import Invitation
from communities.base.meta_db import Community, Participant, ParticipantRole
from communities.base.meta_sio import CommunitiesEventSpace
from communities.utils import check_participant

controller = ResourceController("communities-invitation", path="/communities/")


@controller.route("/<int:community_id>/invitations/index/")
class InvitationLister(Resource):
    @check_participant(controller, role=ParticipantRole.OWNER)
    @controller.argument_parser(counter_parser)
    @controller.lister(20, Invitation.IndexModel)
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


class InvitePreview(PydanticModel):
    joined: bool
    authorized: bool
    community: Community.IndexModel = None


@controller.route("/join/<code>/")
class InvitationJoin(Resource):
    @controller.jwt_authorizer(User, optional=True)
    @check_invitation()
    @controller.marshal_with(InvitePreview)
    def get(self, user: User, invitation: Invitation | None, community: Community):
        return InvitePreview(
            joined=invitation is None,
            authorized=user is not None,
            community=Community.IndexModel.convert(community),
        )

    @controller.doc_abort(400, "User has already joined")
    @controller.jwt_authorizer(User)
    @check_invitation()
    @controller.marshal_with(Community.IndexModel)
    def post(self, user: User, invitation: Invitation | None, community: Community):
        if invitation is None:
            controller.abort(400, "User has already joined")

        Participant.add(
            community_id=community.id,
            user_id=user.id,
            role=invitation.role,
        )
        if invitation.limit == 1:
            invitation.delete()
        elif invitation.limit is not None:
            invitation.limit -= 1

        CommunitiesEventSpace.new_community.emit_convert(
            community, include_self=True, user_id=user.id
        )

        return community
