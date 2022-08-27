from __future__ import annotations

from enum import Enum
from functools import wraps
from os import getenv

from flask import request
from flask_restx import Resource, Model
from flask_restx.fields import Integer, String as StringField
from flask_restx.reqparse import RequestParser
from itsdangerous import URLSafeSerializer, BadSignature

from common import User, ResourceController, ResponseDoc
from .feedback_db import Feedback, FeedbackType, FeedbackImage

controller = ResourceController("feedback", path="/feedback/")
feedback_serializer: URLSafeSerializer = URLSafeSerializer(
    getenv("JWT_SECRET_KEY", "local only")
)  # TODO redo


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
    parser.add_argument("data", required=True, type=dict)
    parser.add_argument("code", required=False)

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
        session,
        user: User | None,
        feedback_type: str,
        data: dict,
        code: str | None,
    ):
        feedback_type = FeedbackType.from_string(feedback_type)
        if feedback_type is None:
            controller.abort(400, "Unsupported feedback type")

        if code is not None:
            try:
                user_id: int = feedback_serializer.loads(code)
            except BadSignature:
                return self.Responses.BAD_SIGNATURE
            if user is None or user.id != user_id:
                user = User.find_by_id(session, user_id)
            if user is None:
                return self.Responses.USER_NOT_FOUND
        elif user is None:
            return self.Responses.NO_AUTH_PROVIDED

        Feedback.create(session, user_id=user.id, type=feedback_type, data=data)
        return self.Responses.SUCCESS


@controller.route("/images/")
class ImageAttacher(Resource):
    @controller.doc_file_param("image")
    @controller.doc_responses(ResponseDoc(model=Model("ID Response", {"id": Integer})))
    def post(self, session):
        image_id = FeedbackImage.create(session).id
        with open(f"../files/images/feedback-{image_id}.png", "wb") as f:
            f.write(request.data)
        return {"id": image_id}


@controller.route("/dump/")
class FeedbackDumper(Resource):
    @controller.jwt_authorizer(User)
    @controller.marshal_list_with(Feedback.FullModel)
    def get(self, session, user: User):
        if user.email != "admin@admin.admin":
            controller.abort(403, "Permission denied")
        return Feedback.dump_all(session)


def generate_code(user_id: int):
    return feedback_serializer.dumps(user_id)


@controller.with_begin
def dumps_feedback(session) -> list[dict]:
    return controller.marshal(Feedback.dump_all(session), Feedback.FullModel)
