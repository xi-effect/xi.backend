from flask import send_from_directory
from flask_restful import Resource

from componets import jwt_authorizer
from users import User


class AvatarViewer(Resource):  # GET /authors/<int:user_id>/avatar/ (temp, change to /users/.../)
    @jwt_authorizer(User, None, use_session=False)
    def get(self, user_id: int):
        return send_from_directory(r"../files/avatars", f"{user_id}.png")
