from __future__ import annotations

from flask_restx import Resource

from common import ResourceController
from .meta_db import Community
from .meta_utl import check_participant_role

controller = ResourceController("communities-meta", path="/communities/")


@controller.route("/<int:community_id>/")
class CommunityReader(Resource):
    @check_participant_role(controller)
    @controller.marshal_with(Community.IndexModel)
    def get(self, community: Community):
        return community
