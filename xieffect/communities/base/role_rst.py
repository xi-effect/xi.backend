from __future__ import annotations

from flask_restx import Resource

from common import ResourceController
from .meta_db import Community
from .role_db import Role
from ..utils import check_participant

controller = ResourceController(
    "communities-roles", path="/communities/<int:community_id>/"
)


@controller.route("/roles/")
class RolesLister(Resource):
    @check_participant(controller)
    @controller.marshal_list_with(Role.FullModel)
    def get(self, community: Community):
        return Role.find_by_community(community_id=community.id)
