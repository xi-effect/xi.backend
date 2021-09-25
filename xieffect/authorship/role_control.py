from flask_restful import Resource

from componets import jwt_authorizer, with_session
from users import User
from .user_roles import Author


class AuthorInitializer(Resource):  # [GET] /authors/permit/
    @jwt_authorizer(User)
    def get(self, session, user: User):
        return {"a": not Author.find_or_create(session, user).banned}
