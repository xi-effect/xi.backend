from flask_restx import Resource, Namespace

from componets import jwt_authorizer, a_response
from users import User
from .user_roles import Author

authors_namespace: Namespace = Namespace("authors", path="/authors")


@authors_namespace.route("/permit/")
class AuthorInitializer(Resource):  # [GET] /authors/permit/
    @a_response(authors_namespace)
    @jwt_authorizer(User)
    def get(self, session, user: User) -> bool:
        return Author.initialize(session, user)
