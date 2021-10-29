from flask import send_from_directory
from flask_restx import Resource

from componets import Namespace
from users import User

profiles_namespace: Namespace = Namespace("profiles", path="/users/<int:user_id>/")
profile_view = profiles_namespace.model("Profile", User.marshal_models["profile"])


@profiles_namespace.route("/avatar/")
class AvatarViewer(Resource):  # GET /authors/<int:user_id>/avatar/ (temp, change to /users/.../)
    @profiles_namespace.jwt_authorizer(User, check_only=True, use_session=False)  # will it delete user_id?
    def get(self, user_id: int):
        """ Loads user's avatar """
        return send_from_directory(r"../files/avatars", f"{user_id}.png")


@profiles_namespace.route("/profile/")
class ProfileViewer(Resource):
    @profiles_namespace.jwt_authorizer(User, check_only=True, use_session=False)
    @profiles_namespace.database_searcher(User, result_field_name="profile_viewer")
    @profiles_namespace.marshal_with(profile_view)
    def get(self, user: User, profile_viewer: User):
        """Get profile """
        return profile_viewer


