from flask import request, send_from_directory
from flask_restx import Resource
from flask_restx.reqparse import RequestParser

from componets import Namespace, password_parser, ResponseDoc
from users.database import User
# from users.emailer import send_generated_email

settings_namespace: Namespace = Namespace("settings")
other_settings_namespace: Namespace = Namespace("settings", path="/")  # redo (unite with settings_namespace)
protected_settings_namespace: Namespace = Namespace("settings", path="/")
full_settings = settings_namespace.model("FullSettings", User.marshal_models["full-settings"])
main_settings = settings_namespace.model("MainSettings", User.marshal_models["main-settings"])
role_settings = settings_namespace.model("RoleSettings", User.marshal_models["role-settings"])


@other_settings_namespace.route("/avatar/")
class Avatar(Resource):  # [GET|POST] /avatar/
    @other_settings_namespace.doc_responses(ResponseDoc(404, "Avatar not found"))
    @other_settings_namespace.jwt_authorizer(User, use_session=False)
    def get(self, user: User):
        return send_from_directory(r"../files/avatars", f"{user.id}.png")

    @other_settings_namespace.a_response()
    @other_settings_namespace.jwt_authorizer(User, use_session=False)
    def post(self, user: User) -> None:
        with open(f"files/avatars/{user.id}.png", "wb") as f:
            f.write(request.data)


@settings_namespace.route("/")
class Settings(Resource):  # [GET|POST] /settings/
    parser: RequestParser = RequestParser()
    parser.add_argument("changed", type=dict, location="json", required=True, help="A dict of changed settings")

    @settings_namespace.jwt_authorizer(User, use_session=False)
    @settings_namespace.marshal_with(full_settings, skip_none=True)
    def get(self, user: User):
        return user

    @settings_namespace.a_response()
    @settings_namespace.jwt_authorizer(User, use_session=False)
    @settings_namespace.argument_parser(parser)  # fix with json (marshal?)
    def post(self, user: User, changed: dict) -> None:
        user.change_settings(changed)


@settings_namespace.route("/main/")
class MainSettings(Resource):  # [GET] /settings/main/
    @settings_namespace.jwt_authorizer(User, use_session=False)
    @settings_namespace.marshal_with(main_settings, skip_none=True)
    def get(self, user: User):
        return user


@settings_namespace.route("/roles/")
class RoleSettings(Resource):  # [GET] /settings/roles/
    @settings_namespace.jwt_authorizer(User, use_session=False)
    @settings_namespace.marshal_with(role_settings, skip_none=True)
    def get(self, user: User):
        return user


@protected_settings_namespace.route("/email-change/")
class EmailChanger(Resource):  # [POST] /email-change/
    parser: RequestParser = password_parser.copy()
    parser.add_argument("new-email", dest="new_email", required=True, help="Email to be connected to the user")

    @protected_settings_namespace.a_response()
    @protected_settings_namespace.jwt_authorizer(User)
    @protected_settings_namespace.argument_parser(parser)
    def post(self, session, user: User, password: str, new_email: str) -> str:
        if not User.verify_hash(password, user.password):
            return "Wrong password"

        if User.find_by_email_address(session, new_email):
            return "Email in use"

        # send_generated_email(new_email, "confirm", "registration-email.html")
        user.change_email(session, new_email)  # close all other JWT sessions
        return "Success"


@protected_settings_namespace.route("/password-change/")
class PasswordChanger(Resource):  # [POST] /password-change/
    parser: RequestParser = password_parser.copy()
    parser.add_argument("new-password", dest="new_password", required=True, help="Password to be used by user in future")

    @protected_settings_namespace.a_response()
    @protected_settings_namespace.jwt_authorizer(User, use_session=False)
    @protected_settings_namespace.argument_parser(parser)
    def post(self, user: User, password: str, new_password: str) -> str:
        if User.verify_hash(password, user.password):
            user.change_password(new_password)
            return "Success"
        else:
            return "Wrong password"
