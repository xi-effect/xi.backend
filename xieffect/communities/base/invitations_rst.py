from datetime import datetime
from functools import wraps
from typing import Union

from flask_restx import Resource
from flask_restx.reqparse import RequestParser

from common import ResourceController, counter_parser, User
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


def check_invitation(join: bool = False):
    def check_invitation_wrapper(function):
        @wraps(function)
        @invitation_join_namespace.jwt_authorizer(User)
        @invitation_join_namespace.marshal_with(Community.IndexModel)
        def check_invitation_inner(*_, user, code, session):
            invitation: Invitation = Invitation.find_by_code(session, code)
            if invitation is None:  # TODO still get the community id and check if joined
                invitation_join_namespace.abort(400, "Invalid invitation")
            if Participant.find_by_ids(session, invitation.community_id, user.id):
                invitation_join_namespace.abort(400, "User has already joined")  # TODO return the community id

            if invitation.deadline is not None and invitation.deadline < datetime.utcnow() or invitation.limit == 0:
                invitation.delete(session)
                invitation_join_namespace.abort(400, "Invalid invitation")

            if join:
                Participant.create(session, invitation.community_id, user.id, invitation.role)
                if invitation.limit == 1:
                    invitation.delete(session)
                elif invitation.limit is not None:
                    invitation.limit -= 1

            return invitation.community

        return check_invitation_inner

    return check_invitation_wrapper


@invitation_join_namespace.route("/<code>/")
class InvitationJoin(Resource):
    @check_invitation()
    def get(self):
        pass

    @check_invitation(join=True)
    def post(self):
        pass
