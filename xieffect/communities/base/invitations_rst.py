from flask_restx import Resource
from flask_restx.reqparse import RequestParser

from common import Namespace, counter_parser, User
from .invitations_db import Invitations
from .meta_db import Community

communities_namespace: Namespace = Namespace("communities-invitation", path="/invitation/")
community_base = communities_namespace.model("CommunityBase", Community.marshal_models["community-base"])


@communities_namespace.route("/")
class InvitationCreator(Resource):
    parser: RequestParser = RequestParser()
    parser.add_argument("name", required=True, type=str)
    parser.add_argument("description", required=False, type=str)

    @communities_namespace.jwt_authorizer(User)
    @communities_namespace.argument_parser(parser)
    @communities_namespace.a_response()
    def post(self, session, community_id: int, limit: int, time: str, role: int) -> bool:
        Invitations.create(session, Community.find_by_id(session, community_id), role, limit, time)
        return True  # temp
