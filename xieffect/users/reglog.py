from flask import Response, jsonify
from flask_jwt_extended import create_access_token, set_access_cookies
from flask_jwt_extended import get_jwt, jwt_required, unset_jwt_cookies
from flask_restx import Resource, Namespace
from flask_restx.reqparse import RequestParser

from componets import password_parser, argument_parser, with_session
from users.database import TokenBlockList, User
# from users.emailer import send_generated_email, parse_code

reglog_namespace: Namespace = Namespace("reglog", path="/")


@reglog_namespace.route("/reg/")
class UserRegistration(Resource):  # [POST] /reg/
    parser = password_parser.copy()
    parser.add_argument("email", required=True)
    parser.add_argument("username", required=True)

    @with_session
    @argument_parser(parser, "email", "username", "password", ns=reglog_namespace)
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
    parser.add_argument("email", required=True, help="email is required")

    @with_session
    @argument_parser(parser, "email", "password", ns=reglog_namespace)
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
    @with_session
    @jwt_required()
    def post(self, session):
        response = jsonify({"a": True})
        TokenBlockList.add_by_jti(session, get_jwt()["jti"])
        unset_jwt_cookies(response)
        return response


@reglog_namespace.route("/password-reset/<email>/")
class PasswordResetSender(Resource):  # [GET] /password-reset/<email>/
    @with_session
    def get(self, session, email: str):
        if not User.find_by_email_address(session, email) or email == "admin@admin.admin":
            return {"a": False}
        # send_generated_email(email, "pass", "password-reset-email.html")
        return {"a": True}


@reglog_namespace.route("/password-reset/confirm/")
class PasswordReseter(Resource):  # [POST] /password-reset/confirm/
    parser: RequestParser = password_parser.copy()
    parser.add_argument("code", required=True)

    @with_session
    @argument_parser(parser, "code", "password", ns=reglog_namespace)
    def post(self, session, code: str, password: str):
        # email = parse_code(code, "pass")
        # if email is None:
        #     return {"a": "Code error"}

        user: User = User.find_by_email_address(session, email)
        if not user:
            return {"a": "User doesn't exist"}

        user.change_password(password)
        return {"a": "Success"}
