from functools import wraps

from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_restx import Resource, Model
from flask_restx.fields import Integer
from flask_restx.reqparse import RequestParser

from common import Namespace, counter_parser, ResponseDoc, with_session, get_or_pop, User
from .invitations_db import Invite
from .meta_db import Community, Participant

invitations_namespace: Namespace = Namespace("invitations", path="/communities/")
invitations_model = invitations_namespace.model("Invite", Invite.marshal_models["community_invites"])


@invitations_namespace.route("/communities/<int:community_id>/invitations/")
class InviteCreator(Resource):
    parser: RequestParser = RequestParser()
    parser.add_argument("limit", type=int, required=True)
    parser.add_argument("role", type=Participant, required=True)
    parser.add_argument("time_limit", required=True)

    @invitations_namespace.doc_responses(ResponseDoc(model=Model("ID Response", {"id": Integer})))
    @invitations_namespace.jwt_authorizer(User)
    @invitations_namespace.argument_parser(parser)
    @invitations_namespace.database_searcher(Community)
    def post(self, session, community: Community, limit: int, role: Participant, time_limit: int):
        return {"id": Invite.create(session, community, role, limit, time_limit).invite_id}


@invitations_namespace.route("/communities/")
class GlobalInviteManager(Resource):
    parser: RequestParser = RequestParser()
    parser.add_argument("start", type=int, required=True)
    parser.add_argument("finish", type=int, required=True)

    @invitations_namespace.jwt_authorizer(User)
    @invitations_namespace.argument_parser(counter_parser)
    @invitations_namespace.lister(50, invitations_model)
    def post(self, session, start: int, finish: int):
        return Invite.find_global(session, start, finish)


@invitations_namespace.route("/communities/")
class InviteAccept(Resource):
    @invitations_namespace.jwt_authorizer(User)
    def post(self, session, acceptor: User):
        return Invite.accept(session, acceptor)


@invitations_namespace.route("/communities/<int:community_id>/invitations/<int:invite_id>/")
class InviteDelete(Resource):
    @invitations_namespace.jwt_authorizer(User)
    @invitations_namespace.database_searcher(Invite)
    @invitations_namespace.marshal_with(invitations_model)
    def delete(self, session, invite: Invite):
        invite.delete(session)
