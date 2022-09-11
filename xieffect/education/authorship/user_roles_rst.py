from __future__ import annotations

from flask_restx import Resource
from flask_restx.reqparse import RequestParser

from common import ResourceController, User
from .user_roles_db import Author

controller = ResourceController("authors", path="/authors")


@controller.route("/permit/")
class AuthorInitializer(Resource):  # [GET] /authors/permit/
    @controller.jwt_authorizer(User)
    @controller.a_response()
    def get(self, user: User) -> bool:
        """Adds Author role to the User (requester).
        Does nothing, if it has been added before. Will fail if Author was banned."""
        return Author.initialize(user)


@controller.route("/settings/")
class ChangeAuthorSetting(Resource):
    @controller.jwt_authorizer(Author)
    @controller.marshal_with(Author.SettingsModel)
    def get(self, author: Author):
        return author

    parser: RequestParser = RequestParser()
    parser.add_argument("pseudonym", required=False)

    @controller.jwt_authorizer(Author)
    @controller.argument_parser(parser)
    @controller.a_response()
    def post(self, author: Author, pseudonym: str) -> None:
        author.pseudonym = pseudonym
