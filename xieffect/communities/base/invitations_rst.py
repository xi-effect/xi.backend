import datetime

from flask_restx import Resource
from flask_restx.reqparse import RequestParser

from common import Namespace, counter_parser, User
from .invitations_db import Invitation
from .meta_db import Community, Participant, ParticipantRole

invitation_namespace = Namespace("communities-invitation", path="/communities/<int:community_id>/invitations/")
community_base = invitation_namespace.model("CommunityBase", Community.marshal_models["community-base"])
invitation_base = invitation_namespace.model("InvitationBase", Invitation.marshal_models["invitation-base"])

invitation_join_namespace = Namespace("communities-invitation", path="/communities/join/")


@invitation_namespace.route("/")
class InvitationCreator(Resource):
    parser: RequestParser = RequestParser()
    parser.add_argument("role", required=True, choices=ParticipantRole.get_all_field_names(), type=str)
    parser.add_argument("limit", required=False, type=int)
    parser.add_argument("time", required=False, type=int)

    @invitation_namespace.jwt_authorizer(User)
    @invitation_namespace.argument_parser(parser)
    @invitation_namespace.database_searcher(Community, use_session=True)
    @invitation_namespace.a_response()
    def post(self, session, community: Community, user: User, limit: int, time: int, role: str) -> str:
        if role is None:
            invitation_namespace.abort(400, "Invalid role")

        participant = Participant.find_by_ids(session, community.id, user.id)
        if participant is not None and participant.role == ParticipantRole.OWNER:
            due_date = datetime.datetime.now().date() + datetime.timedelta(days=time)
            return Invitation.create(session, community.id, ParticipantRole.from_string(role), limit, due_date).code
        return "This user can't create invitation to this community"


@invitation_namespace.route("/index/")
class InvitationLister(Resource):
    @invitation_namespace.jwt_authorizer(User, check_only=True)
    @invitation_namespace.argument_parser(counter_parser)
    @invitation_namespace.lister(20, invitation_base)
    def post(self, session, community_id: int, start: int, finish: int):
        return Invitation.find_by_community_id(session, Community.find_by_id(session, community_id).id, start,
                                               finish - start)


@invitation_namespace.route("/<int:invitation_id>/")
class InvitaionManager(Resource):
    @invitation_namespace.jwt_authorizer(User, check_only=True)
    @invitation_namespace.database_searcher(Invitation, use_session=True)
    @invitation_namespace.a_response()
    def delete(self, session, invitation: Invitation, **_) -> None:
        invitation.delete(session)


@invitation_join_namespace.route("/<code>/")
class InvitationJoin(Resource):
    @invitation_join_namespace.jwt_authorizer(User, check_only=True)
    @invitation_join_namespace.marshal_with(community_base)
    def get(self, session, code: str):
        invitation = Invitation.find_by_code(session, code)
        return Community.find_by_id(session, invitation.community_id)

    @invitation_join_namespace.jwt_authorizer(User)
    @invitation_join_namespace.a_response()
    def post(self, session, user: User, code: str) -> str:
        invitation = Invitation.find_by_code(session, code)
        if invitation is None:
            return "This invitation is invalid"
        if Participant.find_by_ids(session, invitation.community_id, user.id) is not None:
            return "This user have joined already"
        else:
            if invitation.check_availabel(datetime.datetime.now()):
                if invitation.count_limit != 0:
                    Participant.create(session, invitation.community_id, user.id, invitation.role)
                    if invitation.count_limit > 0:
                        invitation.count_limit -= 1
                    return "User joined successfully"
                else:
                    invitation.delete(session)
                    return "This invitation is invalid"
            else:
                invitation.delete(session)
                return "This invitation is invalid"
