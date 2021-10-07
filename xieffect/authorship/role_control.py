from flask_restx import Resource

from componets import Namespace
from users import User
from .user_roles import Author

authors_namespace: Namespace = Namespace("authors", path="/authors")


@authors_namespace.route("/permit/")
class AuthorInitializer(Resource):  # [GET] /authors/permit/
    @authors_namespace.a_response()
    @authors_namespace.jwt_authorizer(User)
    def get(self, session, user: User) -> bool:
        return Author.initialize(session, user)
