from flask import Response, jsonify
from flask_jwt_extended import create_access_token, set_access_cookies
from flask_jwt_extended import get_jwt, jwt_required, unset_jwt_cookies
from flask_restful import Resource
from flask_restful.reqparse import RequestParser

from database import TokenBlockList, User
from emailer import send_generated_email, parse_code
from base.parsers import password_parser
from base.checkers import argument_parser


class UserRegistration(Resource):
    parser = password_parser.copy()
    parser.add_argument("email", required=True)
    parser.add_argument("username", required=True)

    @argument_parser(parser, "email", "username", "password")
    def post(self, email: str, username: str, password: str):
        user: User = User.create(email, username, password)
        if not user:
            return {"a": False}

        send_generated_email(email, "confirm", "registration-email.html")

        response = jsonify({"a": True})
        set_access_cookies(response, create_access_token(identity=user.id))
        return response

        # except: return {"a": False}, 500


class UserLogin(Resource):
    parser: RequestParser = password_parser.copy()
    parser.add_argument("email", required=True, help="email is required")

    @argument_parser(parser, "email", "password")
    def post(self, email: str, password: str):
        # print(f"Tried to login as '{email}' with password '{password}'")

        user: User = User.find_by_email_address(email)
        if not user:
            return {"a": "User doesn't exist"}

        if User.verify_hash(password, user.password):
            response: Response = jsonify({"a": "Success"})
            set_access_cookies(response, create_access_token(identity=user.id))
            return response
        else:
            return {"a": "Wrong password"}


class UserLogout(Resource):
    @jwt_required()
    def post(self):
        response = jsonify({"a": True})
        TokenBlockList.add_by_jti(get_jwt()["jti"])
        unset_jwt_cookies(response)
        return response


class PasswordResetSender(Resource):
    def get(self, email: str):
        if not User.find_by_email_address(email) or email == "admin@admin.admin":
            return {"a": False}
        send_generated_email(email, "pass", "password-reset-email.html")
        return {"a": True}


class PasswordReseter(Resource):
    parser: RequestParser = password_parser.copy()
    parser.add_argument("code", required=True)

    @argument_parser(parser, "code", "password")
    def post(self, code: str, password: str):
        email = parse_code(code, "pass")
        if email is None:
            return {"a": "Code error"}

        user: User = User.find_by_email_address(email)
        if not user:
            return {"a": "User doesn't exist"}

        user.change_password(password)
        return {"a": "Success"}
