from __future__ import annotations

from flask_fullstack import RequestParser
from flask_restx import Resource

from common import User
from moderation import MUBController, permission_index
from other import EmailType, send_code_email

qa_section = permission_index.add_section("quality assurance")
emailing = permission_index.add_permission(qa_section, "emailing")
controller = MUBController("emailer", path="/emailer/")


@controller.route("/send/")
class EmailQAResource(Resource):  # TODO pragma: no coverage (action)
    parser = RequestParser()
    parser.add_argument(
        "user-email",
        dest="user_email",
        required=False,
    )
    parser.add_argument(
        "tester-email",
        dest="tester_email",
        required=True,
    )
    parser.add_argument(
        "type",
        dest="email_type",
        type=EmailType.as_input(),
        required=True,
    )

    @controller.doc_abort(400, "Unsupported type")
    @controller.doc_abort(404, "User not found")
    @controller.require_permission(emailing, use_moderator=False)
    @controller.argument_parser(parser)
    @controller.a_response()
    def post(
        self,
        user_email: str | None,
        tester_email: str,
        email_type: EmailType,
    ) -> str:
        if user_email is None:
            user_email = tester_email
        user = User.find_by_email_address(user_email)
        if user is None:
            controller.abort(404, "User not found")

        if email_type != EmailType.PASSWORD:
            user.email_confirmed = False
        return send_code_email(tester_email, email_type)
