from flask_restx import Resource

from componets import Namespace
from users import User
from .user_roles import Author, Moderator

authors_namespace: Namespace = Namespace("authors", path="/authors")
settings_namespace: Namespace = Namespace("setting", path="/")

@authors_namespace.route("/permit/")
class AuthorInitializer(Resource):  # [GET] /authors/permit/
    @authors_namespace.a_response()
    @authors_namespace.jwt_authorizer(User)
    def get(self, session, user: User) -> bool:
        return Author.initialize(session, user)


@authors_namespace.route("/<int:author_id>/ban/")
class BanAuthor(Resource):
    @authors_namespace.a_response()
    @authors_namespace.jwt_authorizer(Moderator, chek_only=True)
    def post(self, session, author_id: int) -> None:
        author: Author = Author.find_by_id(session, author_id)
        author.banned = True


@authors_namespace.route("/<int:author_id>/unban/")
class UnbanAuthor(Resource):
    @authors_namespace.a_response()
    @authors_namespace.jwt_authorizer(Moderator, chek_only=True)
    def post(self, session, author_id: int) -> None:
        author: Author = Author.find_by_id(session, author_id)
        author.banned = False


@authors_namespace.route("/settings-author/")
class ChangeAuthorSetting(Resource):
    @authors_namespace.a_response()
    @authors_namespace.jwt_authorizer(User, use_session=False)
    def get(self) -> None:
        author: Author = Author.pseudonym
        return author


    def post(self, authors: Author, new_psewdonum: str) -> str:
        author: Author = authors.pseudonym
        author = new_psewdonum
        return author
