from __future__ import annotations

from flask_fullstack import counter_parser
from flask_restx import Resource

from common import ResourceController
from .videochat_db import CommunityParticipant, CommunityMessage
from ..utils import check_participant, Community

controller = ResourceController(
    "communities-videochat", path="/communities/<int:community_id>/videochat/"
)


@controller.route("/participants/")
class ParticipantsList(Resource):
    @check_participant(controller)
    @controller.marshal_list_with(CommunityParticipant.IndexModel)
    def get(self, community: Community):
        return CommunityParticipant.find_by_community(community.id)


@controller.route("/messages/")
class MessagesList(Resource):
    @check_participant(controller)
    @controller.argument_parser(counter_parser)
    @controller.lister(20, CommunityMessage.IndexModel)
    def get(self, community: Community, start: int, finish: int):
        return CommunityMessage.find_by_ids(community.id, start, finish - start)
