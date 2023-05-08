from __future__ import annotations

from flask_fullstack import password_parser, RequestParser
from flask_restx import Resource, inputs

from common import ResourceController, User
from communities.base.users_ext_db import CommunitiesUser
from other import create_email_confirmer, EmailType, send_code_email
from vault import File

controller = ResourceController("settings", path="/users/me/")


@controller.route("/profile/")
class Settings(Resource):
    parser: RequestParser = RequestParser()
    parser.add_argument("username", type=str, required=False)
    parser.add_argument("handle", type=str, required=False)
    parser.add_argument("name", type=str, required=False)
    parser.add_argument("surname", type=str, required=False)
    parser.add_argument("patronymic", type=str, required=False)
    parser.add_argument("birthday", type=inputs.date_from_iso8601, required=False)

    @controller.jwt_authorizer(User)
    @controller.marshal_with(User.ProfileData)
    def get(self, user: User) -> User:
        """Loads user's own full settings"""
        return user

    @controller.doc_abort(200, "Handle already in use")
    @controller.jwt_authorizer(User)
    @controller.argument_parser(parser)
    @controller.a_response()
    def post(
        self,
        user: User,
        birthday: str | None,
        handle: str | None,
        **kwargs,
    ) -> str:
        if User.find_by_handle(handle, user.id) is not None:
            return "Handle already in use"
        user.change_settings(birthday=birthday, handle=handle, **kwargs)
        return "Success"


@controller.route("/avatar/")
class AvatarChanger(Resource):
    parser: RequestParser = RequestParser()
    parser.add_argument(
        "avatar-id",
        dest="avatar_id",
        required=False,
        type=int,
    )

    @controller.jwt_authorizer(User)
    @controller.argument_parser(parser)
    @controller.database_searcher(File, input_field_name="avatar_id")
    @controller.a_response()
    def post(self, user: User, file: File) -> None:
        profile = CommunitiesUser.find_by_id(user.id)
        profile.avatar_id = file.id

    @controller.jwt_authorizer(User)
    @controller.a_response()
    def delete(self, user: User) -> None:
        user = CommunitiesUser.find_by_id(user.id)
        user.avatar.delete()


@controller.route("/email/")
class EmailChanger(Resource):
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


@controller.route("/password/")
class PasswordChanger(Resource):
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
