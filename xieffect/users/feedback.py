from typing import Union

from flask_restx import Resource, marshal
from flask_restx.reqparse import RequestParser
from itsdangerous import URLSafeSerializer, BadSignature

from componets import Namespace, unite_models, with_session
from main import app
from .database import User, Feedback, FeedbackType

feedback_namespace: Namespace = Namespace("feedback", path="/feedback/")
feedback_serializer: URLSafeSerializer = URLSafeSerializer(app.config["JWT_SECRET_KEY"])
feedback_json = feedback_namespace.model("Feedback", unite_models(
    User.marshal_models["full-settings"], Feedback.marshal_models["feedback-full"]))


@feedback_namespace.route("/")
class FeedbackSaver(Resource):
    parser = RequestParser()
    parser.add_argument("type", required=True, choices=FeedbackType.get_all_field_names(), dest="feedback_type")
    parser.add_argument("data", required=True, type=dict)
    parser.add_argument("code", required=False)

    @feedback_namespace.jwt_authorizer(User, optional=True)
    @feedback_namespace.argument_parser(parser)
    @feedback_namespace.a_response()
    def post(self, session, user: Union[User, None], feedback_type: str, data: dict, code: Union[str, None]) -> str:
        feedback_type = FeedbackType.from_string(feedback_type)
        if feedback_type is None:
            feedback_namespace.abort(400, "Unsupported type")

        if user is None:
            if code is None:
                return "Neither the user is authorized, nor the code is provided"
            try:
                user_id: int = feedback_serializer.loads(code)
            except BadSignature:
                return "Bad code signature"
            user = User.find_by_id(session, user_id)
            if user is None:
                return "Code refers to non-existing user"
        Feedback.create(session, user, feedback_type, data)
        return "Success"


def generate_code(user_id: int):
    return feedback_serializer.dumps(user_id)


@with_session
def dumps_feedback(session) -> list[dict]:
    return marshal(Feedback.dump_all(session), feedback_json)
