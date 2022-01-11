from enum import Enum
from functools import wraps
from typing import Union, Type

from flask import request
from flask_restx import Resource, marshal, Model
from flask_restx.fields import Integer, String as StringField
from flask_restx.reqparse import RequestParser
from itsdangerous import URLSafeSerializer, BadSignature

from common import User, Namespace, unite_models, with_session, ResponseDoc
from main import app
from .database import Feedback, FeedbackType, FeedbackImage

feedback_namespace: Namespace = Namespace("feedback", path="/feedback/")
feedback_serializer: URLSafeSerializer = URLSafeSerializer(app.config["JWT_SECRET_KEY"])
feedback_json = feedback_namespace.model("Feedback", unite_models(
    User.marshal_models["full-settings"], Feedback.marshal_models["feedback-full"]))


def enum_response(enum: Type[Enum]):
    model = {"a": StringField(enum=[member.value for member in enum.__members__.values()])}
    model = feedback_namespace.model(enum.__name__, model=model)

    def enum_response_wrapper(function):
        @feedback_namespace.response(*ResponseDoc(model=model).get_args())
        @wraps(function)
        def enum_response_inner(*args, **kwargs):
            return {"a": function(*args, **kwargs).value}

        return enum_response_inner

    return enum_response_wrapper


@feedback_namespace.route("/")
class FeedbackSaver(Resource):
    parser = RequestParser()
    parser.add_argument("type", required=True, choices=FeedbackType.get_all_field_names(), dest="feedback_type")
    parser.add_argument("data", required=True, type=dict)
    parser.add_argument("code", required=False)

    class Responses(Enum):
        SUCCESS = "Success"
        BAD_SIGNATURE = "Bad code signature"
        USER_NOT_FOUND = "Code refers to non-existing user"
        NO_AUTH_PROVIDED = "Neither the user is authorized, nor the code is provided"

    @feedback_namespace.jwt_authorizer(User, optional=True)
    @feedback_namespace.argument_parser(parser)
    @enum_response(Responses)
    def post(self, session, user: Union[User, None], feedback_type: str, data: dict, code: Union[str, None]):
        feedback_type = FeedbackType.from_string(feedback_type)
        if feedback_type is None:
            feedback_namespace.abort(400, "Unsupported feedback type")

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

        Feedback.create(session, user, feedback_type, data)
        return self.Responses.SUCCESS


@feedback_namespace.route("/images/")
class ImageAttacher(Resource):
    @feedback_namespace.doc_file_param("image")
    @feedback_namespace.doc_responses(ResponseDoc(model=Model("ID Response", {"id": Integer})))
    def post(self, session):
        image_id = FeedbackImage.create(session).id
        with open(f"../files/images/feedback-{image_id}.png", "wb") as f:
            f.write(request.data)
        return {"id": image_id}


@feedback_namespace.route("/dump/")
class FeedbackDumper(Resource):
    @feedback_namespace.jwt_authorizer(User)
    @feedback_namespace.marshal_list_with(feedback_json)
    def get(self, session, user: User):
        if user.email != "admin@admin.admin":
            feedback_namespace.abort(403, "Permission denied")
        return Feedback.dump_all(session)


def generate_code(user_id: int):
    return feedback_serializer.dumps(user_id)


@with_session
def dumps_feedback(session) -> list[dict]:
    return marshal(Feedback.dump_all(session), feedback_json)
