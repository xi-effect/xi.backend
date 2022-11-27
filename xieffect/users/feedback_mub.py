from __future__ import annotations

from flask_fullstack import counter_parser
from flask_restx import Resource

from moderation import MUBController, permission_index
from .feedback_db import Feedback, FeedbackType

feedback_section = permission_index.add_section("feedback")
read_feedback = permission_index.add_permission(feedback_section, "read feedback")
manage_feedback = permission_index.add_permission(feedback_section, "manage feedback")
controller = MUBController("feedback")


@controller.route("/")
class FeedbackDumper(Resource):
    parser = counter_parser.copy()
    parser.add_argument("user-id", dest="user_id", required=False)
    parser.add_argument(
        "type",
        dest="feedback_type",
        choices=FeedbackType.get_all_field_names(),
        required=False,
    )

    @controller.require_permission(read_feedback, use_moderator=False)
    @controller.argument_parser(parser)
    @controller.lister(50, Feedback.FullModel)
    def get(
        self,
        start: int,
        finish: int,
        user_id: int | None,
        feedback_type: str | None,
    ) -> list[Feedback]:
        if feedback_type is not None:
            feedback_type = FeedbackType.from_string(feedback_type)
        return Feedback.search_by_params(start, finish - start, user_id, feedback_type)


@controller.route("/<int:feedback_id>/")
class FeedbackManager(Resource):
    @controller.require_permission(read_feedback, use_moderator=False)
    @controller.database_searcher(Feedback)
    @controller.marshal_with(Feedback.FullModel)
    def get(self, feedback: Feedback):
        return feedback

    @controller.require_permission(manage_feedback, use_moderator=False)
    @controller.database_searcher(Feedback)
    @controller.a_response()
    def delete(self, feedback: Feedback) -> None:
        feedback.delete()
