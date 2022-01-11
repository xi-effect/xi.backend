from flask_restx import Resource
from flask_restx.reqparse import RequestParser

from common import Namespace, User
from .user_roles import Author, Moderator

authors_namespace: Namespace = Namespace("authors", path="/authors")
author_settings_model = Author.marshal_models["author-settings"]
author_settings_view = authors_namespace.model("AuthorSettings", author_settings_model)


@authors_namespace.route("/permit/")
class AuthorInitializer(Resource):  # [GET] /authors/permit/
    @authors_namespace.jwt_authorizer(User)
    @authors_namespace.a_response()
    def get(self, session, user: User) -> bool:
        """ Adds Author role to the User (requester).
        Does nothing, if it has been added before. Will fail if Author was banned. """
        return Author.initialize(session, user)


@authors_namespace.route("/<int:author_id>/ban/")
class BanAuthor(Resource):
    @authors_namespace.jwt_authorizer(Moderator, check_only=True)
    @authors_namespace.a_response()
    def post(self, session, author_id: int) -> None:
        author: Author = Author.find_by_id(session, author_id)
        author.banned = True


@authors_namespace.route("/<int:author_id>/unban/")
class UnbanAuthor(Resource):
    @authors_namespace.jwt_authorizer(Moderator, check_only=True)
    @authors_namespace.a_response()
    def post(self, session, author_id: int) -> None:
        author: Author = Author.find_by_id(session, author_id)
        author.banned = False


@authors_namespace.route("/settings/")
class ChangeAuthorSetting(Resource):
    @authors_namespace.jwt_authorizer(Author, use_session=False)
    @authors_namespace.marshal_with(author_settings_view)
    def get(self, author: Author):
        return author

    parser: RequestParser = RequestParser()
    parser.add_argument("pseudonym", required=False)

    @authors_namespace.jwt_authorizer(Author, use_session=False)
    @authors_namespace.argument_parser(parser)
    @authors_namespace.a_response()
    def post(self, author: Author, pseudonym: str) -> None:
        author.pseudonym = pseudonym
