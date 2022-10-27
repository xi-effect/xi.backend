from __future__ import annotations

from flask_fullstack import counter_parser
from flask_restx import Resource
from flask_restx.reqparse import RequestParser

from common import ResourceController, User

controller = ResourceController("profiles", path="/users/")


@controller.route("/")
class UserFinder(Resource):
    parser: RequestParser = counter_parser.copy()
    parser.add_argument("search", type=str, required=False)

    @controller.jwt_authorizer(User)
    @controller.argument_parser(parser)
    @controller.lister(10, User.IndexProfile)
    def post(self, user: User, search: str | None, start: int, finish: int):
        return User.search_by_username(user.id, search, start, finish - start)


@controller.route("/<int:user_id>/profile/")
class ProfileViewer(Resource):
    @controller.jwt_authorizer(User, check_only=True)
    @controller.database_searcher(User, result_field_name="profile_viewer")
    @controller.marshal_with(User.FullProfile)
    def get(self, profile_viewer: User):
        """Get profile"""
        return profile_viewer
