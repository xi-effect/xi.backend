from __future__ import annotations

from flask_restx import Resource

from common import ResourceController
from .meta_db import Community
from ..utils import check_participant

controller = ResourceController("communities-meta", path="/communities/")


@controller.route("/<int:community_id>/")
class CommunityReader(Resource):
    @controller.doc_abort(403, "Not a member")
    @check_participant(controller)
    @controller.marshal_with(Community.IndexModel)
    def get(self, community: Community):
        return community
