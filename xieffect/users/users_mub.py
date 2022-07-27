from __future__ import annotations

from flask import request, send_from_directory, redirect
from flask_restx import Resource
from flask_restx.reqparse import RequestParser

from common import sessionmaker, User, ResponseDoc, counter_parser
from moderation import MUBController, permission_index

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
