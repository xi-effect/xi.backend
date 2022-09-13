from __future__ import annotations

from functools import wraps

from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restx import Resource
from flask_restx.reqparse import RequestParser

from common import counter_parser, ResourceController, User
from .invites_db import Invite

controller = ResourceController("invites", path="/invites/")


def admin_only():
    def admin_only_wrapper(function):
        @controller.doc_aborts(*controller.auth_errors)
        @controller.doc_abort("403 ", "Permission denied")
        @controller.doc(security="jwt")
        @wraps(function)
        @jwt_required()
        def admin_only_inner(*args, **kwargs):
            admin = User.find_by_id(get_jwt_identity()[""])
            if admin is None or admin.email != "admin@admin.admin":
                return {"a": "Permission denied"}, 403
            return function(*args, **kwargs)

        return admin_only_inner

    return admin_only_wrapper


@controller.route("/")
class InviteCreator(Resource):
    parser: RequestParser = RequestParser()
    parser.add_argument("name", type=str, required=True)
    parser.add_argument("limit", type=int, required=False)

    @admin_only()
    @controller.argument_parser(parser)
    @controller.marshal_with(Invite.IDModel)
    def post(self, name: str, limit: int):
        return Invite.create(name=name, limit=limit or -1)


@controller.route("/index/")
class GlobalInviteManager(Resource):
    @admin_only()
    @controller.argument_parser(counter_parser)
    @controller.lister(50, Invite.IndexModel)
    def post(self, start: int, finish: int):
        return Invite.find_global(start, finish)


@controller.route("/<int:invite_id>/")
class InviteManager(Resource):
    parser: RequestParser = RequestParser()
    parser.add_argument("name", type=str, required=False)
    parser.add_argument("limit", type=int, required=False)

    @admin_only()
    @controller.database_searcher(Invite)
    @controller.marshal_with(Invite.IndexModel)
    def get(self, invite: Invite):
        return invite

    @admin_only()
    @controller.argument_parser(parser)
    @controller.database_searcher(Invite)
    @controller.a_response()
    def put(self, name: str, limit: int, invite: Invite) -> None:
        if name is not None:
            invite.name = name
        if limit is not None:
            invite.limit = limit

    @admin_only()
    @controller.database_searcher(Invite)
    @controller.a_response()
    def delete(self, invite: Invite) -> None:
        invite.delete()
