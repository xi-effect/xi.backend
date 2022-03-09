import datetime

from flask_restx import Resource
from flask_restx.reqparse import RequestParser

from common import Namespace, counter_parser, User
from .invitations_db import Invitation
from .meta_db import Community, Participant, ParticipantRole

invitation_namespace = Namespace("communities-invitation", path="/communities/<int:community_id>/invitations/")
community_base = invitation_namespace.model("CommunityBase", Community.marshal_models["community-base"])
invitation_base = invitation_namespace.model("InvitationBase", Invitation.marshal_models["invitation-base"])


@invitation_namespace.route("/")
class InvitationCreator(Resource):
    parser: RequestParser = RequestParser()
    parser.add_argument("role", required=True, type=int)
    parser.add_argument("limit", required=False, type=int)
    parser.add_argument("time", required=False, type=int)

    @invitation_namespace.jwt_authorizer(User)
    @invitation_namespace.argument_parser(parser)
    @invitation_namespace.database_searcher(Community, use_session=True)
    def post(self, session, community: Community, user: User, limit: int, time: int, role: int):
        access = False
        if Participant.find_by_ids(session, community.id, user.id):
            if Participant.find_by_ids(session, community.id, user.id).role == ParticipantRole.OWNER:
                access = True
        if access:
            due_date = datetime.datetime.now().date() + datetime.timedelta(days=time)
            i = Invitation.create(session, community.id, role, limit, due_date)
            result = i.get_code()
        else:
            result = "This user can't create invitation to this community"
        return result  # temp


@invitation_namespace.route("/get_list/")
class InvitationLister(Resource):
    @invitation_namespace.jwt_authorizer(User, check_only=True)
    @invitation_namespace.argument_parser(counter_parser)
    @invitation_namespace.database_searcher(Community, use_session=True)
    @invitation_namespace.lister(20, invitation_base)
    def post(self, session, community: Community, start: int, finish: int):
        return Invitation.find_invitation_by_community_id(session, community.id, start, finish - start)


@invitation_namespace.route("/<int:invitation_id>/")
class InvitaionManager(Resource):
    @invitation_namespace.jwt_authorizer(User, check_only=True)
    @invitation_namespace.database_searcher(Invitation, use_session=True)
    @invitation_namespace.a_response()
    def delete(self, session, invitation: Invitation, community_id: int) -> None:
        invitation.delete(session)

    @invitation_namespace.jwt_authorizer(User, check_only=True)
    @invitation_namespace.marshal_with(community_base)
    def post(self, session, invitation_id: int, community_id: int):
        return Invitation.find_community_by_id(session, community_id)


@invitation_namespace.route("/<string:url>/join/")
class InvitationJoin(Resource):
    @invitation_namespace.jwt_authorizer(User)
    @invitation_namespace.database_searcher(Community, use_session=True)
    def post(self, session, community: Community, user: User, url: str):
        access = True
        invitation = Invitation.get_invitation_by_url(session, url)
        if Participant.find_by_ids(session, community.id, user.id):
            access = False
        if access:
            if invitation.count_limit != 0:
                Participant.create(session, community.id, user.id)
                if invitation.count_limit > 0:
                    invitation.count_limit -= 1
                result = "User joined successfully"
            else:
                invitation.delete(session)
                result = "This invitation invalid"
        else:
            result = "This user have joined already"
        return result

