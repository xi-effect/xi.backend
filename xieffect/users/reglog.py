from flask import Response, jsonify
from flask_jwt_extended import create_access_token, set_access_cookies
from flask_jwt_extended import get_jwt, jwt_required, unset_jwt_cookies
from flask_restx import Resource
from flask_restx.reqparse import RequestParser

from componets import password_parser, Namespace, with_session, success_response, message_response
from users.database import TokenBlockList, User
# from users.emailer import send_generated_email, parse_code

reglog_namespace: Namespace = Namespace("reglog", path="/")


@reglog_namespace.route("/reg/")
class UserRegistration(Resource):  # [POST] /reg/
    parser: RequestParser = password_parser.copy()
    parser.add_argument("email", required=True, help="Email to be connected to new user's account")
    parser.add_argument("username", required=True, help="Username to be assigned to new user's account")

    @reglog_namespace.doc_responses(success_response)
    @with_session
    @reglog_namespace.argument_parser(parser)
    def post(self, session, email: str, username: str, password: str):
        user: User = User.create(session, email, username, password)
        if not user:
            return {"a": False}

        # send_generated_email(email, "confirm", "registration-email.html")

        response = jsonify({"a": True})
        set_access_cookies(response, create_access_token(identity=user.id))
        return response

        # except: return {"a": False}, 500


@reglog_namespace.route("/auth/")
class UserLogin(Resource):  # [POST] /auth/
    parser: RequestParser = password_parser.copy()
    parser.add_argument("email", required=True, help="User's email")

    @with_session
    @reglog_namespace.doc_responses(message_response)
    @reglog_namespace.argument_parser(parser)
    def post(self, session, email: str, password: str):
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
    @reglog_namespace.doc_responses(success_response)
    @with_session
    @jwt_required()
    def post(self, session):
        response = jsonify({"a": True})
        TokenBlockList.add_by_jti(session, get_jwt()["jti"])
        unset_jwt_cookies(response)
        return response


@reglog_namespace.route("/password-reset/<email>/")
class PasswordResetSender(Resource):  # [GET] /password-reset/<email>/
    @reglog_namespace.a_response()
    @with_session
    def get(self, session, email: str) -> bool:
        return User.find_by_email_address(session, email) is not None and email != "admin@admin.admin"


@reglog_namespace.route("/password-reset/confirm/")
class PasswordReseter(Resource):  # [POST] /password-reset/confirm/
    parser: RequestParser = password_parser.copy()
    parser.add_argument("code", required=True, help="Code sent in the email")

    @reglog_namespace.a_response()
    @with_session
    @reglog_namespace.argument_parser(parser)
    def post(self, session, code: str, password: str) -> str:
        # email = parse_code(code, "pass")
        # if email is None:
        #     return "Code error"

        user: User = User.find_by_email_address(session, email)
        if not user:
            return "User doesn't exist"

        user.change_password(password)
        return "Success"
