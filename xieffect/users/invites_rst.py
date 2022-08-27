from functools import wraps

from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_restx import Resource, Model
from flask_restx.fields import Integer
from flask_restx.reqparse import RequestParser

from common import ResourceController, counter_parser, ResponseDoc, get_or_pop, User
from .invites_db import Invite

controller = ResourceController("invites", path="/invites/")


def admin_only(use_session: bool = False):
    def admin_only_wrapper(function):
        @controller.doc_aborts(*controller.auth_errors)
        @controller.doc_abort("403 ", "Permission denied")
        @controller.doc(security="jwt")
        @wraps(function)
        @jwt_required()
        @controller.with_begin
        def admin_only_inner(*args, **kwargs):
            admin = User.find_by_id(get_or_pop(kwargs, "session", use_session), get_jwt_identity()[""])
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

    @controller.doc_responses(ResponseDoc(model=Model("ID Response", {"id": Integer})))
    @admin_only(use_session=True)
    @controller.argument_parser(parser)
    def post(self, session, name: str, limit: int):
        return {"id": Invite.create(session, name=name, limit=limit or -1).id}


@controller.route("/index/")
class GlobalInviteManager(Resource):
    @admin_only(use_session=True)
    @controller.argument_parser(counter_parser)
    @controller.lister(50, Invite.IndexModel)
    def post(self, session, start: int, finish: int):
        return Invite.find_global(session, start, finish)


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
    @controller.database_searcher(Invite, use_session=True)
    @controller.a_response()
    def delete(self, session, invite: Invite) -> None:
        invite.delete(session)
