from flask import request, send_from_directory
from flask_restx import Resource, Namespace
from flask_restx.reqparse import RequestParser

from componets import jwt_authorizer, argument_parser, password_parser
from users.database import User
# from users.emailer import send_generated_email

settings_namespace: Namespace = Namespace("settings")


class Avatar(Resource):  # [GET|POST] /avatar/
    @jwt_authorizer(User, use_session=False)
    def get(self, user: User):
        return send_from_directory(r"../files/avatars", f"{user.id}.png")

    @jwt_authorizer(User, use_session=False)
    def post(self, user: User):
        with open(f"files/avatars/{user.id}.png", "wb") as f:
            f.write(request.data)
        return {"a": True}


@settings_namespace.route("/")
class Settings(Resource):  # [GET|POST] /settings/
    parser: RequestParser = RequestParser()
    parser.add_argument("changed", type=dict, location="json", required=True)

    @jwt_authorizer(User, use_session=False)
    @settings_namespace.marshal_with(User.marshal_models["full-settings"])
    def get(self, user: User):
        return user

    @jwt_authorizer(User, use_session=False)
    @argument_parser(parser, "changed")
    def post(self, user: User, changed: dict):
        user.change_settings(changed)
        return {"a": True}


@settings_namespace.route("/main/")
class MainSettings(Resource):  # [GET] /settings/main/
    @jwt_authorizer(User, use_session=False)
    @settings_namespace.marshal_with(User.marshal_models["main-settings"])
    def get(self, user: User):
        return user


@settings_namespace.route("/roles/")
class RoleSettings(Resource):  # [GET] /settings/roles/
    @jwt_authorizer(User)
    def get(self, session, user: User):
        return user.get_role_settings(session)


class EmailChanger(Resource):  # [POST] /email-change/
    parser: RequestParser = password_parser.copy()
    parser.add_argument("new-email", required=True)

    @jwt_authorizer(User)
    @argument_parser(parser, "password", ("new-email", "new_email"))
    def post(self, session, user: User, password: str, new_email: str):
        if not User.verify_hash(password, user.password):
            return {"a": "Wrong password"}

        if User.find_by_email_address(session, new_email):
            return {"a": "Email in use"}

        # send_generated_email(new_email, "confirm", "registration-email.html")
        user.change_email(session, new_email)
        return {"a": "Success"}


class PasswordChanger(Resource):  # [POST] /password-change/
    parser: RequestParser = password_parser.copy()
    parser.add_argument("new-password", required=True)

    @jwt_authorizer(User, use_session=False)
    @argument_parser(parser, "password", ("new-password", "new_password"))
    def post(self, user: User, password: str, new_password: str):
        if User.verify_hash(password, user.password):
            user.change_password(new_password)
            return {"a": "Success"}
        else:
            return {"a": "Wrong password"}
