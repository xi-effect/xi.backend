from __future__ import annotations

from flask_fullstack import counter_parser, RequestParser
from flask_restx import Resource

from common import ResourceController
from .meta_db import Community, Participant
from .utils import check_participant

controller = ResourceController("communities-meta", path="/communities/<int:community_id>/")


@controller.route("/")
class CommunityReader(Resource):  # TODO pragma: no coverage
    @check_participant(controller)
    @controller.marshal_with(Community.IndexModel)
    def get(self, community: Community):
        return community


@controller.route("/participants/")
class ParticipantSearcher(Resource):
    parser: RequestParser = counter_parser.copy()
    parser.add_argument("search", type=str, required=False)

    @check_participant(controller, use_community=True)
    @controller.argument_parser(parser)
    @controller.lister(10, Participant.FullModel)
    def get(self, search: str | None, community: Community, start: int, finish: int):
        return Participant.search_by_username(search, community.id, start, finish - start)
