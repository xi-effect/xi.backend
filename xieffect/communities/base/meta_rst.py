from __future__ import annotations

from flask_restx import Resource
from flask_restx.reqparse import RequestParser

from common import ResourceController, counter_parser, User
from .meta_db import Community, Participant

controller = ResourceController("communities-meta", path="/communities/")


@controller.route("/")
class CommunityCreator(Resource):
    parser: RequestParser = RequestParser()
    parser.add_argument("name", required=True, type=str)
    parser.add_argument("description", required=False, type=str)

    @controller.deprecated
    @controller.jwt_authorizer(User)
    @controller.argument_parser(parser)
    @controller.marshal_with(Community.BaseModel)
    def post(self, session, user: User, name: str, description: str | None):
        return Community.create(session, name, description, user)


@controller.route("/index/")
class CommunityLister(Resource):
    @controller.deprecated
    @controller.jwt_authorizer(User)
    @controller.argument_parser(counter_parser)
    @controller.lister(20, Community.IndexModel)
    def post(self, session, user: User, start: int, finish: int):
        return Community.find_by_user(session, user, start, finish - start)


@controller.route("/<int:community_id>/")
class CommunityReader(Resource):
    @controller.doc_abort(403, "Not a member")
    @controller.jwt_authorizer(User)
    @controller.database_searcher(Community, use_session=True)
    @controller.marshal_with(Community.IndexModel)
    def get(self, session, user, community: Community):
        if Participant.find_by_ids(session, community.id, user.id) is None:
            controller.abort(403, "Not a member")
        return community
