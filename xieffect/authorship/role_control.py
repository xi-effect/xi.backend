from flask_restx import Resource

from componets import Namespace
from users import User
from .user_roles import Author, Moderator

authors_namespace: Namespace = Namespace("authors", path="/authors")


@authors_namespace.route("/permit/")
class AuthorInitializer(Resource):  # [GET] /authors/permit/
    @authors_namespace.a_response()
    @authors_namespace.jwt_authorizer(User)
    def get(self, session, user: User) -> bool:
        """ Adds Author role to the User (requester).
        Does nothing, if it has been added before. Will fail if Author was banned. """
        return Author.initialize(session, user)


@authors_namespace.route("/<int:author.id>/ban/")
class BanAuthor(Resource):
    @authors_namespace.a_response()
    @authors_namespace.jwt_authorizer(Moderator, chek_only=True)
    def post(self, session, author_id: int):
        author: Author = Author.find_by_id(session, author_id)
        author.banned = True


@authors_namespace.route("/<int:author.id>/unban/")
class BanAuthor(Resource):
    @authors_namespace.a_response()
    @authors_namespace.jwt_authorizer(Moderator, chek_only=True)
    def post(self, session, author_id: int):
        author: Author = Author.find_by_id(session, author_id)
        author.banned = False
