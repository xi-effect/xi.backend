from flask_restx import Resource, Namespace

from componets import jwt_authorizer
from users import User
from .user_roles import Author

authors_namespace: Namespace = Namespace("authors", path="/authors")


@authors_namespace.route("/permit/")
class AuthorInitializer(Resource):  # [GET] /authors/permit/
    @jwt_authorizer(User)
    def get(self, session, user: User):
        return {"a": not Author.find_or_create(session, user).banned}
