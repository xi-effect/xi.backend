from flask_restx import Resource

from componets import Namespace
from users.database import User, Invite

invites_namespace: Namespace = Namespace("invites", path="/invites/")


@invites_namespace.route("/mine/")
class Invite(Resource):
    @invites_namespace.jwt_authorizer(User)
    @invites_namespace.a_response()
    def get(self, session, user: User, invite: Invite):
        if self.find_by_id(session, user.invite_id) is None:
            return 404
        else:
            return invite
