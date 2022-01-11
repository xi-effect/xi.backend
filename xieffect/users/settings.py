import os

from flask import request, send_from_directory
from flask_restx import Resource
from flask_restx.reqparse import RequestParser

from common import Namespace, password_parser, ResponseDoc, User
# from users.emailer import send_generated_email

settings_namespace: Namespace = Namespace("settings")
other_settings_namespace: Namespace = Namespace("settings", path="/")  # TODO unite with settings_namespace
protected_settings_namespace: Namespace = Namespace("settings", path="/")

full_settings = settings_namespace.model("FullSettings", User.marshal_models["full-settings"])
main_settings = settings_namespace.model("MainSettings", User.marshal_models["main-settings"])
role_settings = settings_namespace.model("RoleSettings", User.marshal_models["role-settings"])


@other_settings_namespace.route("/avatar/")
class Avatar(Resource):
    @other_settings_namespace.deprecated
    @other_settings_namespace.response(200, "PNG image as a byte string")
    @other_settings_namespace.doc_responses(ResponseDoc(404, "Avatar not found"))
    @other_settings_namespace.jwt_authorizer(User, use_session=False)
    def get(self, user: User):
        """ Loads user's own avatar """
        return send_from_directory(r"../files/avatars", f"{user.id}.png")

    @other_settings_namespace.deprecated
    @other_settings_namespace.doc_file_param("image")
    @other_settings_namespace.jwt_authorizer(User, use_session=False)
    @other_settings_namespace.a_response()
    def post(self, user: User) -> None:
        """ Overwrites user's own avatar """
        with open(f"../files/avatars/{user.id}.png", "wb") as f:
            f.write(request.data)

    @other_settings_namespace.deprecated
    @other_settings_namespace.jwt_authorizer(User, use_session=False)
    @other_settings_namespace.a_response()
    def delete(self, user: User) -> None:
        """Delete avatar"""
        os.remove(f"../files/avatars/{user.id}.png")


def changed(value):
    return dict(value)


changed.__schema__ = {
    "type": "object",
    "format": "changed",
    "example": '{"dark-theme": true | false, ' +
               ", ".join(f'"{key}": ""' for key in ["username", "language", "name", "surname", "patronymic",
                                                    "bio", "group", "avatar"]) + "}"
}


@settings_namespace.route("/")
class Settings(Resource):
    parser: RequestParser = RequestParser()
    parser.add_argument("changed", type=changed, required=True, help="A dict of changed settings")

    @settings_namespace.jwt_authorizer(User, use_session=False)
    @settings_namespace.marshal_with(full_settings, skip_none=True)
    def get(self, user: User):
        """ Loads user's own full settings """
        return user

    @settings_namespace.jwt_authorizer(User, use_session=False)
    @settings_namespace.argument_parser(parser)  # TODO fix with json schema validation
    @settings_namespace.a_response()
    def post(self, user: User, changed: dict) -> None:
        """ Overwrites values in user's settings with ones form payload """
        user.change_settings(changed)


@settings_namespace.route("/main/")
class MainSettings(Resource):
    @settings_namespace.jwt_authorizer(User, use_session=False)
    @settings_namespace.marshal_with(main_settings, skip_none=True)
    def get(self, user: User):
        """ Loads user's own main settings (username, dark-theme and language) """
        return user


@settings_namespace.route("/roles/")
class RoleSettings(Resource):
    @settings_namespace.jwt_authorizer(User, use_session=False)
    @settings_namespace.marshal_with(role_settings, skip_none=True)
    def get(self, user: User):
        """ Loads user's own role settings (author, moderator) """
        return user


@protected_settings_namespace.route("/email-change/")
class EmailChanger(Resource):
    parser: RequestParser = password_parser.copy()
    parser.add_argument("new-email", dest="new_email", required=True, help="Email to be connected to the user")

    @protected_settings_namespace.jwt_authorizer(User)
    @protected_settings_namespace.argument_parser(parser)
    @protected_settings_namespace.a_response()
    def post(self, session, user: User, password: str, new_email: str) -> str:
        """ Verifies user's password and changes user's email to a new one """

        if not User.verify_hash(password, user.password):
            return "Wrong password"

        if User.find_by_email_address(session, new_email):
            return "Email in use"

        # send_generated_email(new_email, "confirm", "registration-email.html")
        user.change_email(session, new_email)  # close all other JWT sessions
        return "Success"


@protected_settings_namespace.route("/password-change/")
class PasswordChanger(Resource):
    parser: RequestParser = password_parser.copy()
    parser.add_argument("new-password", dest="new_password", required=True, help="Password that will be used in future")

    @protected_settings_namespace.jwt_authorizer(User, use_session=False)
    @protected_settings_namespace.argument_parser(parser)
    @protected_settings_namespace.a_response()
    def post(self, user: User, password: str, new_password: str) -> str:
        """ Verifies user's password and changes it to a new one """

        if User.verify_hash(password, user.password):
            user.change_password(new_password)
            return "Success"
        else:
            return "Wrong password"
