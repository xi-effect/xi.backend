from flask import send_from_directory
from flask_restx import Resource, Namespace

from componets import jwt_authorizer
from users import User

profiles_namespace: Namespace = Namespace("profiles", path="/")


@profiles_namespace.route("/authors/<int:user_id>/avatar/")
class AvatarViewer(Resource):  # GET /authors/<int:user_id>/avatar/ (temp, change to /users/.../)
    @jwt_authorizer(profiles_namespace, User, None, use_session=False)
    def get(self, user_id: int):
        return send_from_directory(r"../files/avatars", f"{user_id}.png")
