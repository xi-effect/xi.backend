from __future__ import annotations

from flask_restx import Resource
from common import ResourceController
from .role_db import Role

controller = ResourceController("roles", path="/roles/")


@controller.route("/")
class RolesLister(Resource):
    @controller.doc_abort(403, "Not roles")
    @controller.marshal_list_with(Role.IndexModel)
    def get(self):
        return Role.get_all()
