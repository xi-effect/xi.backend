from __future__ import annotations

from flask_restx import Resource

from common import ResourceController, User
from .meta_db import Community, Participant

controller = ResourceController("communities-meta", path="/communities/")


@controller.route("/<int:community_id>/")
class CommunityReader(Resource):
    @controller.doc_abort(403, "Not a member")
    @controller.jwt_authorizer(User)
    @controller.database_searcher(Community)
    @controller.marshal_with(Community.IndexModel)
    def get(self, user, community: Community):
        if Participant.find_by_ids(community.id, user.id) is None:
            controller.abort(403, "Not a member")
        return community
