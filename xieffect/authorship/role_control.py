from flask_restful import Resource

from componets import jwt_authorizer
from users import User
from .user_roles import Author


class AuthorInitializer(Resource):  # [GET] /authors/permit/
    @jwt_authorizer(User)
    def get(self, user: User):
        return {"a": not Author.find_or_create(user).banned}
