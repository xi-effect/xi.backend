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
    @invites_namespace.argument_parser(parser)
    @invites_namespace.a_response()
    def post(self, session, name: str, limit: int, user: User) -> bool:
        if Invite.find_by_id(session, user.invite_id) is None:
            Invite.create(session, name, limit, user)
            return True

@invites_namespace.route("/global/")
class GlobalInviteManager(Resource):
    @invites_namespace.jwt_authorizer(User)
    @invites_namespace.argument_parser(counter_parser)
    @invites_namespace.lister(10, invites_model)
    def post(self, session, user: User, start: int, finish: int):
        if user.email == "admin@admin.admin":
            return Invite.find_global(session, start, finish)
        else:
            return {"a": "Permission denied"}, 403
