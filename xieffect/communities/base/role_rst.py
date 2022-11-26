from __future__ import annotations

from flask_restx import Resource
from common import ResourceController
from .role_db import Role
from .meta_db import Community

controller = ResourceController(
    "communities-roles", path="/communities/<int:community_id>/"
)


@controller.route("/roles/")
class RolesLister(Resource):
    @controller.database_searcher(Community)
    @controller.marshal_list_with(Role.IndexModel)
    def get(self, community: Community):
        return Role.find_by_community(community_id=community.id)
