from __future__ import annotations

from flask_restx import Resource
from flask_restx.reqparse import RequestParser

from common import sessionmaker, User
from moderation import MUBController, permission_index
from other import EmailType, send_code_email

emailing = permission_index.add_permission("emailing")
controller = MUBController("emailer", path="/emailer/", sessionmaker=sessionmaker)


@controller.route("/send/")
class EmailQAResource(Resource):
    parser = RequestParser()
    parser.add_argument("user-email", dest="user_email", required=False)
    parser.add_argument("tester-email", dest="tester_email", required=True)
    parser.add_argument("type", dest="email_type", choices=EmailType.get_all_field_names(), required=True)

    @controller.doc_abort(400, "Unsupported type")
    @controller.doc_abort(404, "User not found")
    @controller.require_permission(emailing, use_moderator=False)
    @controller.argument_parser(parser)
    def post(self, session, user_email: str | None, tester_email: str, email_type: str):
        email_type = EmailType.from_string(email_type)
        if email_type is None:
            controller.abort(400, f"Unsupported type")

        if user_email is None:
            user_email = tester_email
        user = User.find_by_email_address(session, user_email)
        if user is None:
            controller.abort(404, "User not found")

        if email_type != EmailType.PASSWORD:
            user.email_confirmed = False
        send_code_email(tester_email, email_type)
