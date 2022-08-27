from flask import current_app
from flask_jwt_extended import get_jwt
from flask_restx import Resource
from flask_restx.reqparse import RequestParser
from itsdangerous import BadSignature

from common import password_parser, ResourceController, BlockedToken, User
from communities import CommunitiesUser
from other import EmailType, send_code_email, create_email_confirmer
from .invites_db import Invite

controller = ResourceController("reglog", path="/")


@controller.route("/home/")
class UserHome(Resource):
    @controller.jwt_authorizer(User)
    @controller.marshal_with(CommunitiesUser.FullModel)
    def get(self, session, user: User):
        return CommunitiesUser.find_or_create(session, user.id)


@controller.route("/reg/")
class UserRegistration(Resource):
    parser: RequestParser = password_parser.copy()
    parser.add_argument(
        "email",
        required=True,
        help="Email to be connected to new user's account",
    )
    parser.add_argument(
        "username",
        required=True,
        help="Username to be assigned to new user's account",
    )
    parser.add_argument(
        "code",
        required=True,
        help="Serialized invite code",
    )

    @controller.doc_abort(" 200", "Email already in use")
    @controller.doc_abort("200 ", "Invite code limit exceeded")
    @controller.doc_abort(400, "Malformed code (BadSignature)")
    @controller.doc_abort(404, "Invite not found")
    @controller.with_begin
    @controller.argument_parser(parser)
    @controller.marshal_with_authorization(CommunitiesUser.TempModel)
    def post(self, session, email: str, username: str, password: str, code: str):
        """Creates a new user if email is not used already, logs in automatically"""
        try:
            invite = Invite.find_by_code(session, code)
        except BadSignature:
            return {"a": "Malformed code (BadSignature)"}, 400

        if invite is None:
            return {"a": "Invite not found"}, 404
        if invite.limit == invite.accepted:
            return {"a": "Invite code limit exceeded"}
        invite.accepted += 1

        if (
            user := User.create(
                session,
                email=email,
                username=username,
                password=password,
                invite=invite,
            )
        ) is None:
            return {"a": "Email already in use"}
        send_code_email(email, EmailType.CONFIRM)
        cu = CommunitiesUser.find_or_create(session, user.id)
        return cu, user


EmailConfirmer = create_email_confirmer(
    controller, "/email-confirm/", EmailType.CONFIRM
)


@controller.route("/auth/")
class UserLogin(Resource):
    parser: RequestParser = password_parser.copy()
    parser.add_argument("email", required=True, help="User's email")

    @controller.doc_abort("200 ", "User doesn't exist")
    @controller.doc_abort(" 200", "Wrong password")
    @controller.with_begin
    @controller.argument_parser(parser)
    @controller.marshal_with_authorization(CommunitiesUser.TempModel)
    def post(self, session, email: str, password: str):
        """Tries to log in with credentials given"""
        if (user := User.find_by_email_address(session, email)) is None:
            return {"a": "User doesn't exist"}

        if User.verify_hash(password, user.password):
            cu = CommunitiesUser.find_or_create(session, user.id)
            return cu, user
        return {"a": "Wrong password"}


@controller.route("/go/")
class Test(Resource):
    @controller.with_begin
    @controller.marshal_with_authorization(CommunitiesUser.TempModel)
    def get(self, session):
        """Localhost-only endpoint for logging in from the docs"""
        if not current_app.debug:
            return {"a": False}

        return CommunitiesUser.find_or_create(session, 1), User.find_by_id(session, 1)


@controller.route("/logout/")
class UserLogout(Resource):
    @controller.with_begin
    @controller.removes_authorization()
    def post(self, session):
        """Logs the user out, blocks the token"""
        BlockedToken.create(session, jti=get_jwt()["jti"])
        return {"a": True}


@controller.route("/password-reset/")
class PasswordResetSender(Resource):
    parser: RequestParser = RequestParser()
    parser.add_argument("email", required=True, help="User's email")

    @controller.with_begin
    @controller.argument_parser(parser)
    @controller.a_response()
    def post(self, session, email: str) -> bool:
        """First step of resetting password, tries sending a password-reset email by the address given"""
        user = User.find_by_email_address(session, email)
        if user is not None and email != "admin@admin.admin":
            send_code_email(email, EmailType.PASSWORD)
            return True
        return False


@controller.route("/password-reset/confirm/")
class PasswordReseter(Resource):
    parser: RequestParser = password_parser.copy()
    parser.add_argument("code", required=True, help="Code sent in the email")

    @controller.doc_abort(200, "Success")
    @controller.doc_abort("200 ", "User doesn't exist")
    @controller.doc_abort(" 200", "Code error")
    @controller.with_begin
    @controller.argument_parser(parser)
    @controller.a_response()
    def post(self, session, code: str, password: str) -> str:
        """Second step of resetting password, sets the new password if code is correct"""

        email = EmailType.PASSWORD.parse_code(code)
        if email is None:
            return "Code error"

        if (user := User.find_by_email_address(session, email)) is None:
            return "User doesn't exist"
        user.change_password(password)
        return "Success"
