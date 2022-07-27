from __future__ import annotations

from flask_restx import Resource
from flask_restx.reqparse import RequestParser
from itsdangerous import BadSignature

from common import sessionmaker, User, password_parser, counter_parser, Undefined
from moderation import MUBController, permission_index
from users.invites_db import Invite

manage_users = permission_index.add_permission("manage users")
controller = MUBController("users", sessionmaker=sessionmaker)


@controller.route("/")
class UserIndexResource(Resource):
    parser = counter_parser.copy()
    parser.add_argument("username", required=False)
    parser.add_argument("email", required=False)

    @controller.require_permission(manage_users, use_moderator=False)
    @controller.argument_parser(parser)
    @controller.lister(50, User.FullData)
    def get(self, session, start: int, finish: int, **kwargs: str | None) -> list[User]:
        return User.search_by_params(session, start, finish - start, **kwargs)

    parser: RequestParser = password_parser.copy()
    parser.add_argument("email", required=True, help="Email to be connected to new user's account")
    parser.add_argument("username", required=True, help="Username to be assigned to new user's account")
    parser.add_argument("code", required=False, help="Serialized invite code")

    @controller.require_permission(manage_users, use_moderator=False)
    @controller.argument_parser(parser)
    @controller.marshal_with(User.FullData)
    def post(self, session, email: str, password: str, username: str, code: str | None):
        # TODO check password length and hash
        if code is None:
            from wsgi import TEST_INVITE_ID  # TODO redo without local imports!
            invite = Invite.find_by_id(session, TEST_INVITE_ID)
        else:
            try:
                invite = Invite.find_by_code(session, code)
            except BadSignature:
                return {"a": "Malformed code (BadSignature)"}, 400

            if invite is None:
                return {"a": "Invite not found"}, 404
            if invite.limit == invite.accepted:
                return {"a": "Invite code limit exceeded"}
        invite.accepted += 1

        user = User.create(session, email=email, username=username, password=password, invite=invite)
        return {"a": "Email already in use"} if user is None else user


@controller.route("/<int:user_id>/")
class UserManagerResource(Resource):
    parser = RequestParser()
    parser.add_argument("email-confirmed", dest="email_confirmed", type=bool, store_missing=False)

    @controller.require_permission(manage_users, use_moderator=False)
    @controller.argument_parser(parser, use_undefined=True)
    @controller.database_searcher(User)
    @controller.marshal_with(User.FullData)
    def put(self, user, email_confirmed: bool | Undefined):
        if email_confirmed is not Undefined:
            user.email_confirmed = email_confirmed

    @controller.require_permission(manage_users, use_moderator=False)
    @controller.database_searcher(User)
    @controller.a_response()
    def delete(self) -> None:
        controller.abort(501, "Deleting is not implemented")
