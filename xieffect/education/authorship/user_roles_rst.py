from flask_restx import Resource
from flask_restx.reqparse import RequestParser

from common import ResourceController, User
from .user_roles_db import Author, Moderator

controller = ResourceController("authors", path="/authors")


@controller.route("/permit/")
class AuthorInitializer(Resource):  # [GET] /authors/permit/
    @controller.jwt_authorizer(User)
    @controller.a_response()
    def get(self, session, user: User) -> bool:
        """ Adds Author role to the User (requester).
        Does nothing, if it has been added before. Will fail if Author was banned. """
        return Author.initialize(session, user)


@controller.route("/<int:author_id>/ban/")
class BanAuthor(Resource):
    @controller.jwt_authorizer(Moderator, check_only=True)
    @controller.a_response()
    def post(self, session, author_id: int) -> None:
        author: Author = Author.find_by_id(session, author_id)
        author.banned = True


@controller.route("/<int:author_id>/unban/")
class UnbanAuthor(Resource):
    @controller.jwt_authorizer(Moderator, check_only=True)
    @controller.a_response()
    def post(self, session, author_id: int) -> None:
        author: Author = Author.find_by_id(session, author_id)
        author.banned = False


@controller.route("/settings/")
class ChangeAuthorSetting(Resource):
    @controller.jwt_authorizer(Author, use_session=False)
    @controller.marshal_with(Author.SettingsModel)
    def get(self, author: Author):
        return author

    parser: RequestParser = RequestParser()
    parser.add_argument("pseudonym", required=False)

    @controller.jwt_authorizer(Author, use_session=False)
    @controller.argument_parser(parser)
    @controller.a_response()
    def post(self, author: Author, pseudonym: str) -> None:
        author.pseudonym = pseudonym
