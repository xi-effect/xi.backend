from flask_restx import Resource

from componets import Namespace
from .database import User, Invite

invites_namespace: Namespace = Namespace("invites", path="/invites/")
invites_model = invites_namespace.model("Invite", Invite.marshal_models["invite"])


@invites_namespace.route("/mine/")
class InviteGetter(Resource):
    @invites_namespace.jwt_authorizer(User)
    @invites_namespace.marshal_with(invites_model)
    def get(self, session, user: User):
        invite = Invite.find_by_id(session, user.invite_id)
        if invite is None:
            return {"a": "Invite not found"}, 404
        else:
            return invite
