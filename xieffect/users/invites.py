from functools import wraps

from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_restx import Resource, Model
from flask_restx.fields import Integer
from flask_restx.reqparse import RequestParser

from common import Namespace, counter_parser, ResponseDoc, with_session, get_or_pop, User
from .database import Invite

invites_namespace: Namespace = Namespace("invites", path="/invites/")
invites_model = invites_namespace.model("Invite", Invite.marshal_models["invite"])


def admin_only(use_session: bool = False):
    def admin_only_wrapper(function):
        @invites_namespace.doc_responses(ResponseDoc.error_response(f"403 ", "Permission denied"),
                                         *invites_namespace.auth_errors)
        @invites_namespace.doc(security="jwt")
        @wraps(function)
        @jwt_required()
        @with_session
        def admin_only_inner(*args, **kwargs):
            admin = User.find_by_id(get_or_pop(kwargs, "session", use_session), get_jwt_identity())
            if admin is None or admin.email != "admin@admin.admin":
                return {"a": "Permission denied"}, 403
            return function(*args, **kwargs)

        return admin_only_inner

    return admin_only_wrapper


@invites_namespace.route("/")
class InviteCreator(Resource):
    parser: RequestParser = RequestParser()
    parser.add_argument("name", type=str, required=True)
    parser.add_argument("limit", type=int, required=False)

    @invites_namespace.doc_responses(ResponseDoc(model=Model("ID Response", {"id": Integer})))
    @admin_only(use_session=True)
    @invites_namespace.argument_parser(parser)
    def post(self, session, name: str, limit: int):
        return {"id": Invite.create(session, name, limit).id}


@invites_namespace.route("/index/")
class GlobalInviteManager(Resource):
    @admin_only(use_session=True)
    @invites_namespace.argument_parser(counter_parser)
    @invites_namespace.lister(50, invites_model)
    def post(self, session, start: int, finish: int):
        return Invite.find_global(session, start, finish)


@invites_namespace.route("/<int:invite_id>/")
class InviteManager(Resource):
    parser: RequestParser = RequestParser()
    parser.add_argument("name", type=str, required=False)
    parser.add_argument("limit", type=int, required=False)

    @admin_only()
    @invites_namespace.database_searcher(Invite)
    @invites_namespace.marshal_with(invites_model)
    def get(self, invite: Invite):
        return invite

    @admin_only()
    @invites_namespace.argument_parser(parser)
    @invites_namespace.database_searcher(Invite)
    @invites_namespace.a_response()
    def put(self, name: str, limit: int, invite: Invite) -> None:
        if name is not None:
            invite.name = name
        if limit is not None:
            invite.limit = limit

    @admin_only()
    @invites_namespace.database_searcher(Invite, use_session=True)
    @invites_namespace.a_response()
    def delete(self, session, invite: Invite) -> None:
        invite.delete(session)
