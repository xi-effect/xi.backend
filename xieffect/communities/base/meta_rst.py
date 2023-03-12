from __future__ import annotations

from flask_fullstack import counter_parser, RequestParser
from flask_restx import Resource

from common import ResourceController, User
from .meta_db import Community, Participant
from .utils import check_participant

controller = ResourceController("communities-meta", path="/communities/")


@controller.route("/<int:community_id>/")
class CommunityReader(Resource):  # TODO pragma: no coverage
    @check_participant(controller)
    @controller.marshal_with(Community.IndexModel)
    def get(self, community: Community):
        return community


@controller.route("/")
class ParticipantSearcher(Resource):
    parser: RequestParser = counter_parser.copy()
    parser.add_argument("search", type=str, required=False)

    @controller.jwt_authorizer(User, check_only=True)
    @controller.argument_parser(parser)
    @controller.lister(10, Participant.FullModel)
    def get(self, search: str | None, start: int, finish: int):
        return Participant.search_by_username(search, start, finish - start)
