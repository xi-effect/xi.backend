from flask import Response, jsonify
from flask_jwt_extended import create_access_token, set_access_cookies
from flask_jwt_extended import get_jwt, jwt_required, unset_jwt_cookies
from flask_restx import Resource
from flask_restx.reqparse import RequestParser
from itsdangerous import URLSafeSerializer

from componets import password_parser, Namespace, with_session, success_response
from main import app
from users.database import TokenBlockList, User, Invite

# from users.emailer import send_generated_email, parse_code

reglog_namespace: Namespace = Namespace("reglog", path="/")
success_response.register_model(reglog_namespace)
add_sets_cookie_response = reglog_namespace.response(*success_response.get_args(),
                                                     headers={"SetCookie": "sets access_token_cookie"})
add_unsets_cookie_response = reglog_namespace.response(*success_response.get_args(),
                                                       headers={"SetCookie": "unsets access_token_cookie"})


@reglog_namespace.route("/reg/")
class UserRegistration(Resource):  # [POST] /reg/
    parser: RequestParser = password_parser.copy()
    parser.add_argument("email", required=True, help="Email to be connected to new user's account")
    parser.add_argument("username", required=True, help="Username to be assigned to new user's account")
    parser.add_argument("invite", required=True)

    @with_session
    @add_sets_cookie_response
    @reglog_namespace.argument_parser(parser)
    def post(self, session, email: str, username: str, password: str, invite_code: str):
        """ Creates a new user if email is not used already, logs in automatically """
        safe_serializer = Invite.serializer
        try:
            invite_id = safe_serializer.loads(invite_code)
            invite = Invite.find_by_id(session, invite_id)
            if invite.limit != invite.accepted:
                user: User = User.create(session, email, username, password, invite)
                invite.accepted = invite.accepted + 1
            else:
                return {"a": "limit exceeded"}
            if not user:
                return {"a": "Registration failed, user not created"}

            # send_generated_email(email, "confirm", "registration-email.html")

            response = jsonify({"a": "Success"})
            set_access_cookies(response, create_access_token(identity=user.id))
            return response
            # except: return {"a": False}, 500
        except:
            return {"a": "This code not working"}


@reglog_namespace.route("/auth/")
class UserLogin(Resource):  # [POST] /auth/
    parser: RequestParser = password_parser.copy()
    parser.add_argument("email", required=True, help="User's email")

    @with_session
    @add_sets_cookie_response
    @reglog_namespace.argument_parser(parser)
    def post(self, session, email: str, password: str):
        """ Tries to log in with credentials given """

        # print(f"Tried to login as '{email}' with password '{password}'")

        user: User = User.find_by_email_address(session, email)
        if not user:
            return {"a": "User doesn't exist"}

        if User.verify_hash(password, user.password):
            response: Response = jsonify({"a": "Success"})
            set_access_cookies(response, create_access_token(identity=user.id))
            return response
        else:
            return {"a": "Wrong password"}


@reglog_namespace.route("/logout/")
class UserLogout(Resource):  # [POST] /logout/
    @with_session
    @add_unsets_cookie_response
    @jwt_required()
    def post(self, session):
        """ Logs the user out, blocks the token """
        response = jsonify({"a": True})
        TokenBlockList.add_by_jti(session, get_jwt()["jti"])
        unset_jwt_cookies(response)
        return response


@reglog_namespace.route("/go/")
class Test(Resource):
    @add_sets_cookie_response
    def get(self):
        """ Localhost-only endpoint for logging in from the docs """
        if not app.debug:
            return {"a": False}

        response: Response = jsonify({"a": True})
        set_access_cookies(response, create_access_token(identity=1))
        return response


@reglog_namespace.route("/password-reset/<email>/")
class PasswordResetSender(Resource):  # [GET] /password-reset/<email>/
    @with_session
    @reglog_namespace.a_response()
    def get(self, session, email: str) -> bool:
        """ First step of resetting password, tries sending a password-reset email by the address given """
        return User.find_by_email_address(session, email) is not None and email != "admin@admin.admin"


@reglog_namespace.route("/password-reset/confirm/")
class PasswordReseter(Resource):  # [POST] /password-reset/confirm/
    parser: RequestParser = password_parser.copy()
    parser.add_argument("code", required=True, help="Code sent in the email")

    @with_session
    @reglog_namespace.argument_parser(parser)
    @reglog_namespace.a_response()
    def post(self, session, code: str, password: str) -> str:
        """ Second step of resetting password, sets the new password if code is correct """

        # email = parse_code(code, "pass")
        # if email is None:
        #     return "Code error"

        user: User = User.find_by_email_address(session, email)
        if not user:
            return "User doesn't exist"

        user.change_password(password)
        return "Success"
