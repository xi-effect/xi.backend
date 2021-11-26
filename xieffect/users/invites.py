from flask_restx import Resource
from flask_restx.reqparse import RequestParser

from componets import Namespace, counter_parser
from .database import User, Invite

invites_namespace: Namespace = Namespace("invites", path="/invites/")
invites_model = invites_namespace.model("Invite", Invite.marshal_models["invite"])


@invites_namespace.route("/mine/")
class InviteManager(Resource):
    parser: RequestParser = RequestParser()
    parser.add_argument("name", type=str, required=False)
    parser.add_argument("limit", type=int, required=False)

    @invites_namespace.jwt_authorizer(User)
    @invites_namespace.marshal_with(invites_model)
    def get(self, session, user: User):
        invite = Invite.find_by_id(session, user.invite_id)
        if invite is None:
            return {"a": "Invite not found"}, 404
        else:
            return invite

    @invites_namespace.jwt_authorizer(User)
    @invites_namespace.database_searcher(Invite)
    @invites_namespace.argument_parser(parser)
    def post(self, session, name: str, limit: int, user: User):
        if Invite.name == name:
            return {"a": "Invite with same name has been already created"}
        else:
            return Invite.create(session, name, limit, user)


@invites_namespace.route("/global/")
class GlobalInviteManager(Resource):
    parser: RequestParser = counter_parser.copy()

    @invites_namespace.jwt_authorizer(User)
    @invites_namespace.argument_parser(parser)
    @invites_namespace.lister(10, invites_model)
    def post(self, session, user: User, start: int, finish: int):
        if user.email == "admin@admin.admin":
            return Invite.find_global(session, start, finish)
