from __future__ import annotations

from flask_fullstack import counter_parser, RequestParser
from flask_restx import Resource

from moderation import MUBController, permission_index
from .invites_db import Invite

beta_test_section = permission_index.add_section("beta-test")
manage_invites = permission_index.add_permission(beta_test_section, "manage invites")
controller = MUBController("invites")


@controller.route("/")
class InviteCreator(Resource):
    parser: RequestParser = RequestParser()
    parser.add_argument("name", type=str, required=True)
    parser.add_argument("limit", type=int, required=False)

    @controller.require_permission(manage_invites, use_moderator=False)
    @controller.argument_parser(parser)
    @controller.marshal_with(Invite.IDModel)
    def post(self, name: str, limit: int):
        return Invite.create(name=name, limit=limit or -1)


@controller.route("/index/")
class GlobalInviteManager(Resource):
    @controller.require_permission(manage_invites, use_moderator=False)
    @controller.argument_parser(counter_parser)
    @controller.lister(50, Invite.IndexModel)
    def get(self, start: int, finish: int):
        return Invite.find_global(start, finish)


@controller.route("/<int:invite_id>/")
class InviteManager(Resource):
    parser: RequestParser = RequestParser()
    parser.add_argument("name", type=str, required=False)
    parser.add_argument("limit", type=int, required=False)

    @controller.require_permission(manage_invites, use_moderator=False)
    @controller.database_searcher(Invite)
    @controller.marshal_with(Invite.IndexModel)
    def get(self, invite: Invite):
        return invite

    @controller.require_permission(manage_invites, use_moderator=False)
    @controller.argument_parser(parser)
    @controller.database_searcher(Invite)
    @controller.a_response()
    def put(self, name: str, limit: int, invite: Invite) -> None:
        if name is not None:
            invite.name = name
        if limit is not None:
            invite.limit = limit

    @controller.require_permission(manage_invites, use_moderator=False)
    @controller.database_searcher(Invite)
    @controller.a_response()
    def delete(self, invite: Invite) -> None:
        invite.delete()
