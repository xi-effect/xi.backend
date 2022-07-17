from __future__ import annotations

from functools import wraps
from typing import Union

from flask_restx import Resource
from flask_restx.reqparse import RequestParser

from common import ResourceController, PydanticModel, counter_parser, User, get_or_pop
from .invitations_db import Invitation
from .meta_db import Community, Participant, ParticipantRole

controller = ResourceController("communities-invitation", path="/communities/")


@controller.route("/<int:community_id>/invitations/")
class InvitationCreator(Resource):
    parser: RequestParser = RequestParser()
    parser.add_argument("role", required=True, dest="role_", choices=ParticipantRole.get_all_field_names(), type=str)
    parser.add_argument("limit", required=False, type=int)
    parser.add_argument("days", required=False, type=int)

    @controller.deprecated
    @controller.doc_abort(400, "Invalid role")
    @controller.doc_abort(403, "Permission Denied")
    @controller.jwt_authorizer(User)
    @controller.argument_parser(parser)
    @controller.database_searcher(Community, use_session=True)
    @controller.marshal_with(Invitation.BaseModel)
    def post(self, session, community: Community, user: User, role_: str,
             limit: Union[int, None], days: Union[int, None]):
        role: ParticipantRole = ParticipantRole.from_string(role_)
        if role is None:
            controller.abort(400, f"Invalid role: {role_}")

        participant = Participant.find_by_ids(session, community.id, user.id)
        if participant is None:
            controller.abort(403, "Permission Denied: Participant not found")

        if participant.role.value < ParticipantRole.OWNER.value:
            controller.abort(403, "Permission Denied: Low role")

        return Invitation.create(session, community.id, role, limit, days)


@controller.route("/<int:community_id>/invitations/index/")
class InvitationLister(Resource):
    @controller.jwt_authorizer(User, check_only=True)
    @controller.argument_parser(counter_parser)
    @controller.database_searcher(Community, check_only=True, use_session=True)
    @controller.lister(20, Invitation.IndexModel)
    def post(self, session, community_id: int, start: int, finish: int):
        return Invitation.find_by_community(session, community_id, start, finish - start)


@controller.route("/<int:community_id>/invitations/<int:invitation_id>/")
class InvitationManager(Resource):
    @controller.deprecated
    @controller.jwt_authorizer(User, check_only=True)
    @controller.database_searcher(Invitation, use_session=True)
    @controller.a_response()
    def delete(self, session, invitation: Invitation, **_) -> None:
        invitation.delete(session)


def check_invitation(use_session: bool = False):
    def check_invitation_wrapper(function):
        @wraps(function)
        @controller.doc_abort("400 ", "Invalid invitation")
        def check_invitation_inner(*args, **kwargs):
            code: str = kwargs.pop("code")
            session = get_or_pop(kwargs, "session", use_session)
            user: User = kwargs.get("user", None)

            invitation: Invitation = Invitation.find_by_code(session, code)
            if invitation is None:
                controller.abort(400, "Invalid invitation")
            elif user is not None and Participant.find_by_ids(session, invitation.community_id, user.id) is not None:
                return function(*args, invitation=None, community=invitation.community, **kwargs)
            elif invitation.is_invalid():
                invitation.delete(session)
                controller.abort(400, "Invalid invitation")

            return function(*args, invitation=invitation, community=invitation.community, **kwargs)

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
            community=Community.IndexModel.convert(community)
        )

    @controller.doc_abort(400, "User has already joined")
    @controller.jwt_authorizer(User)
    @check_invitation(use_session=True)
    @controller.marshal_with(Community.IndexModel)
    def post(self, session, user: User, invitation: Invitation | None, community: Community):
        if invitation is None:
            controller.abort(400, "User has already joined")

        Participant.create(session, community.id, user.id, invitation.role)
        if invitation.limit == 1:
            invitation.delete(session)
        elif invitation.limit is not None:
            invitation.limit -= 1

        return community
