from __future__ import annotations

from flask_fullstack import password_parser
from flask_restx import Resource
from flask_restx.reqparse import RequestParser

from common import ResourceController, User
from other import create_email_confirmer, EmailType, send_code_email

controller = ResourceController("settings", path="/")


def changes(value):
    return dict(value)


@controller.route("/settings/")
class Settings(Resource):
    parser: RequestParser = RequestParser()
    parser.add_argument(
        "changed",
        type=changes,
        required=True,
        help="A dict of changed settings",
    )

    @controller.jwt_authorizer(User)
    @controller.marshal_with(User.FullData)
    def get(self, user: User):
        """Loads user's own full settings"""
        return user

    @controller.jwt_authorizer(User)
    @controller.argument_parser(parser)  # TODO fix with json schema validation
    @controller.a_response()
    def post(self, user: User, changed: dict) -> None:
        """Overwrites values in user's settings with ones form payload"""
        user.change_settings(changed)


@controller.route("/email-change/")
class EmailChanger(Resource):  # TODO pragma: no coverage
    parser: RequestParser = password_parser.copy()
    parser.add_argument(
        "new-email",
        dest="new_email",
        required=True,
        help="Email to be connected to the user",
    )

    @controller.doc_abort(200, "Success")
    @controller.doc_abort("200 ", "Wrong password")
    @controller.doc_abort(" 200", "Email in use")
    @controller.jwt_authorizer(User)
    @controller.argument_parser(parser)
    @controller.a_response()
    def post(self, user: User, password: str, new_email: str) -> str:
        """Verifies user's password and changes user's email to a new one"""

        if not User.verify_hash(password, user.password):
            return "Wrong password"

        if User.find_by_email_address(new_email):
            return "Email in use"

        send_code_email(new_email, EmailType.CHANGE)
        user.change_email(new_email)  # close all other JWT sessions
        return "Success"


EmailChangeConfirmer = create_email_confirmer(
    controller, "/email-change-confirm/", EmailType.CHANGE
)


@controller.route("/password-change/")
class PasswordChanger(Resource):  # TODO pragma: no coverage
    parser: RequestParser = password_parser.copy()
    parser.add_argument(
        "new-password",
        dest="new_password",
        required=True,
        help="Password that will be used in future",
    )

    @controller.doc_abort(200, "Success")
    @controller.doc_abort("200 ", "Wrong password")
    @controller.jwt_authorizer(User)
    @controller.argument_parser(parser)
    @controller.a_response()
    def post(self, user: User, password: str, new_password: str) -> str:
        """Verifies user's password and changes it to a new one"""

        if User.verify_hash(password, user.password):
            user.change_password(new_password)
            return "Success"
        return "Wrong password"
