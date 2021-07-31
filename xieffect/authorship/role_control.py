from flask_restful import Resource

from componets import jwt_authorizer
from users import User
from .user_roles import Author


class AuthorInitializer(Resource):  # [GET] /authors/permit/
    @jwt_authorizer(User)
    def get(self, user: User):
        user_id: int = user.id
        author: Author = Author.find_by_id(user_id)
        if author is None:
            Author.create(user_id)
        return {"a": not author.banned}
