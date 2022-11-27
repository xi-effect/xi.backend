from __future__ import annotations
from enum import Enum
from functools import wraps
from os import getenv

from flask_restx import Resource
from flask_restx.fields import String as StringField
from flask_restx.reqparse import RequestParser
from itsdangerous import URLSafeSerializer, BadSignature

from common import User, ResourceController, ResponseDoc
from vault import File
from .feedback_db import Feedback, FeedbackType

controller = ResourceController("feedback")
feedback_serializer: URLSafeSerializer = URLSafeSerializer(
    getenv("JWT_SECRET_KEY", "local only")
)


def enum_response(enum: type[Enum]):  # TODO move to ffs
    model = {
        "a": StringField(enum=[member.value for member in enum.__members__.values()])
    }
    model = controller.model(enum.__name__, model=model)

    def enum_response_wrapper(function):
        @controller.response(*ResponseDoc(model=model).get_args())
        @wraps(function)
        def enum_response_inner(*args, **kwargs):
            return {"a": function(*args, **kwargs).value}

        return enum_response_inner

    return enum_response_wrapper


@controller.route("/")
class FeedbackSaver(Resource):
    parser = RequestParser()
    parser.add_argument(
        "type",
        required=True,
        choices=FeedbackType.get_all_field_names(),
        dest="feedback_type",
    )
    parser.add_argument(
        "data",
        required=True,
        type=dict,
    )
    parser.add_argument(
        "files",
        required=False,
        type=int,
        action="append",
    )
    parser.add_argument(
        "code",
        required=False,
    )

    class Responses(Enum):
        SUCCESS = "Success"
        BAD_SIGNATURE = "Bad code signature"
        USER_NOT_FOUND = "Code refers to non-existing user"
        NO_AUTH_PROVIDED = "Neither the user is authorized, nor the code is provided"

    @controller.jwt_authorizer(User, optional=True)
    @controller.argument_parser(parser)
    @enum_response(Responses)
    def post(
        self,
        user: User | None,
        feedback_type: str,
        data: dict,
        files: list[int],
        code: str | None,
    ):
        if len(files) > 10:  # TODO pragma: no coverage
            controller.abort(413, "Too much files")

        feedback_type = FeedbackType.from_string(feedback_type)
        feedback_files = File.find_by_ids(files)

        if len(feedback_files) != len(files):
            controller.abort(404, "Files don't exist")
        if code is not None:
            try:
                user_id: int = feedback_serializer.loads(code)
            except BadSignature:
                return self.Responses.BAD_SIGNATURE
            if user is None or user.id != user_id:
                user = User.find_by_id(user_id)
            if user is None:
                return self.Responses.USER_NOT_FOUND
        elif user is None:
            return self.Responses.NO_AUTH_PROVIDED

        feedback = Feedback.create(user_id=user.id, type=feedback_type, data=data)
        feedback.add_files(feedback_files)
        return self.Responses.SUCCESS


def generate_code(user_id: int):
    return feedback_serializer.dumps(user_id)
