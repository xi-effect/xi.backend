from __future__ import annotations

from flask_fullstack import counter_parser
from flask_restx import Resource

from common import ResourceController
from .videochat_db import ChatParticipant, ChatMessage
from ..base import Community, check_participant

controller = ResourceController(
    "cs-videochat", path="/communities/<int:community_id>/videochat/"
)


@controller.route("/participants/")
class ParticipantsList(Resource):  # pragma: no coverage
    @check_participant(controller)
    @controller.marshal_list_with(ChatParticipant.IndexModel)
    def get(self, community: Community):
        return ChatParticipant.find_by_community(community.id)


@controller.route("/messages/")
class MessagesList(Resource):  # pragma: no coverage
    @check_participant(controller)
    @controller.argument_parser(counter_parser)
    @controller.lister(20, ChatMessage.IndexModel)
    def get(self, community: Community, start: int, finish: int):
        return ChatMessage.find_by_ids(community.id, start, finish - start)
