from typing import Optional

from flask import send_from_directory
from flask_restx import Resource
from flask_restx.reqparse import RequestParser

from componets import Namespace, counter_parser
from users import User

users_namespace: Namespace = Namespace("profiles", path="/users/")
user_index_view = users_namespace.model("UserIndex", User.marshal_models["user-index"])

profiles_namespace: Namespace = Namespace("profiles", path="/users/<int:user_id>/")
profile_view = profiles_namespace.model("Profile", User.marshal_models["profile"])


@users_namespace.route("/")
class UserFinder(Resource):
    parser: RequestParser = counter_parser.copy()
    parser.add_argument("search", type=str, required=False)

    @users_namespace.jwt_authorizer(User, use_session=True)
    @users_namespace.argument_parser(parser)
    @users_namespace.lister(10, user_index_view)
    def post(self, session, user: User, search: Optional[str], start: int, finish: int):
        return User.search_by_username(session, user.id, search, start, finish - start)


@profiles_namespace.route("/avatar/")
class AvatarViewer(Resource):  # GET /authors/<int:user_id>/avatar/ (temp, change to /users/.../)
    @profiles_namespace.deprecated
    @profiles_namespace.jwt_authorizer(User, check_only=True, use_session=False)  # will it delete user_id?
    def get(self, user_id: int):
        """ Loads user's avatar """
        return send_from_directory(r"../files/avatars", f"{user_id}.png")


@profiles_namespace.route("/profile/")
class ProfileViewer(Resource):
    @profiles_namespace.jwt_authorizer(User, check_only=True, use_session=False)
    @profiles_namespace.database_searcher(User, result_field_name="profile_viewer")
    @profiles_namespace.marshal_with(profile_view)
    def get(self, profile_viewer: User):
        """Get profile """
        return profile_viewer
