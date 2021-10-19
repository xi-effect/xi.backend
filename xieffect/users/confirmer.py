from flask_restx import Resource
from flask_restx.reqparse import RequestParser

from componets import Namespace, with_session, message_response
from users.database import User
# from users.emailer import send_generated_email, parse_code

email_namespace: Namespace = Namespace("email", path="/")


@email_namespace.route("/email/<email>/")
class EmailSender(Resource):  # [POST] /email/<email>/
    @email_namespace.doc_responses(message_response)
    @with_session
    def post(self, session, email: str):
        user: User = User.find_by_email_address(session, email)
        if user is None:
            return {"a": User.not_found_text}, 404
        if user.email_confirmed:
            return {"a": "Confirmed"}
        # if timeout
        #     return {"a": "Too fast"}

        # send_generated_email(email, "confirm", "registration-email.html")
        return {"a": "Success"}


@email_namespace.route("/email-confirm/")  # redo?
class EmailConfirm(Resource):  # [POST] /email-confirm/
    parser: RequestParser = RequestParser()
    parser.add_argument("code", required=True, help="Code sent in the email")

    @email_namespace.doc_responses(message_response)
    @with_session
    @email_namespace.argument_parser(parser)
    def post(self, session, code: str):
        # email = parse_code(code, "confirm")
        # if email is None:
        #     return {"a": "Code error"}

        return {"a": "It's not supposed to work..."}

        user: User = User.find_by_email_address(session, email)
        if user is None:
            return {"a": User.not_found_text}, 404

        user.confirm_email()
        return {"a": "Success"}
