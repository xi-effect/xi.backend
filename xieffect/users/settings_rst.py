from __future__ import annotations

from datetime import datetime
from flask_fullstack import password_parser
from flask_restx import Resource
from flask_restx.reqparse import RequestParser

from vault import File
from common import ResourceController, User
from other import create_email_confirmer, EmailType, send_code_email
from communities.base.users_ext_db import CommunitiesUser

controller = ResourceController("settings", path="/")


@controller.route("/settings/")
class Settings(Resource):
    parser: RequestParser = RequestParser()
    parser.add_argument("username", type=str, required=False)
    parser.add_argument("handle", type=str, required=False)
    parser.add_argument("name", type=str, required=False)
    parser.add_argument("surname", type=str, required=False)
    parser.add_argument("patronymic", type=str, required=False)
    parser.add_argument("birthday", type=str, required=False)

    @controller.jwt_authorizer(User)
    @controller.marshal_with(User.SettingData)
    def get(self, user: User):
        """Loads user's own full settings"""
        return user

    @controller.jwt_authorizer(User)
    @controller.argument_parser(parser)  # TODO fix with json schema validation
    @controller.a_response()
    def post(
        self,
        user: User,
        username: str | None,
        handle: str | None,
        name: str | None,
        surname: str | None,
        patronymic: str | None,
        birthday: str | None,
    ) -> None:
        if birthday is not None:
            birthday = datetime.fromisoformat(birthday)
        user.change_settings(
            username=username,
            handle=handle,
            name=name,
            surname=surname,
            patronymic=patronymic,
            birthday=birthday,
        )


@controller.route("/avatar/")
class AvatarChanger(Resource):
    parser: RequestParser = RequestParser()
    parser.add_argument(
        "avatar-id",
        dest="avatar_id",
        required=False,
        type=int,
    )

    @controller.doc_abort(200, "Success")
    @controller.doc_abort(404, "File doesn't exist")
    @controller.jwt_authorizer(User)
    @controller.argument_parser(parser)
    @controller.a_response()
    def post(self, user: User, avatar_id: int):
        file = File.find_by_id(avatar_id)
        if file is None or file.uploader_id != user.id:
            controller.abort(404, "File doesn't exist")
        user = CommunitiesUser.find_by_id(user.id)
        user.avatar_id = avatar_id
        return "Success"

    @controller.doc_abort(200, "Success")
    @controller.jwt_authorizer(User)
    @controller.a_response()
    def delete(self, user: User):
        user = CommunitiesUser.find_by_id(user.id)
        file = File.find_by_id(user.avatar_id)
        file.delete()
        return "Success"


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
