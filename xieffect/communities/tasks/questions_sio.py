from __future__ import annotations

from typing import Any

from flask_fullstack import DuplexEvent, EventSpace
from flask_socketio import join_room, leave_room

from common import EventController
from communities.base import check_permission, PermissionType
from communities.tasks.tests_db import Test, Question, QuestionKind
from communities.tasks.tests_sio import TestsEventSpace
from communities.tasks.utils import test_finder, question_finder

controller = EventController()


@controller.route()
class QuestionsEventSpace(EventSpace):
    @classmethod
    def room_name(cls, test_id: int) -> str:
        return f"cs-questions-{test_id}"

    @controller.argument_parser(TestsEventSpace.TestIdModel)
    @check_permission(controller, PermissionType.MANAGE_TASKS)
    @test_finder(controller)
    @controller.force_ack()
    def open_questions(self, test: Test):
        join_room(self.room_name(test.id))

    @controller.argument_parser(TestsEventSpace.TestIdModel)
    @check_permission(controller, PermissionType.MANAGE_TASKS)
    @test_finder(controller)
    @controller.force_ack()
    def close_questions(self, test: Test):
        leave_room(self.room_name(test.id))

    class CreationModel(Question.BaseModel, TestsEventSpace.TestIdModel):
        pass

    @controller.argument_parser(CreationModel)
    @controller.mark_duplex(Question.FullModel, use_event=True)
    @check_permission(controller, PermissionType.MANAGE_TASKS)
    @test_finder(controller)
    @controller.marshal_ack(Question.FullModel)
    def new_question(
        self,
        event: DuplexEvent,
        test: Test,
        text: str,
        kind: QuestionKind,
    ) -> Question:
        question = Question.create(text, kind, test.id)
        event.emit_convert(question, self.room_name(test.id))
        return question

    class QuestionIdModel(TestsEventSpace.TestIdModel):
        question_id: int

    class UpdateModel(QuestionIdModel):
        kind: str = None
        text: str = None

        # Override dict method of BaseModel to set "exclude_none" argument on True
        def dict(self, *args, **kwargs) -> dict[str, Any]:  # noqa: A003
            kwargs["exclude_none"] = True
            return super().dict(*args, **kwargs)

    @controller.doc_abort(400, "Is not a valid QuestionKind")
    @controller.argument_parser(UpdateModel)
    @controller.mark_duplex(Question.BaseModel, use_event=True)
    @check_permission(controller, PermissionType.MANAGE_TASKS)
    @question_finder(controller)
    @controller.marshal_ack(Question.FullModel)
    def update_question(
        self,
        event: DuplexEvent,
        question: Question,
        **kwargs,
    ) -> Question:
        raw_kind: str | None = kwargs.get("kind")

        if raw_kind is not None:
            kind: QuestionKind = QuestionKind.from_string(raw_kind)
            if kind is None:
                controller.abort(400, f"{raw_kind} is not a valid QuestionKind")
            kwargs["kind"] = kind

        question.update(**kwargs)
        event.emit_convert(question, room=self.room_name(question.id))
        return question

    @controller.argument_parser(QuestionIdModel)
    @controller.mark_duplex(Question.BaseModel, use_event=True)
    @check_permission(controller, PermissionType.MANAGE_TASKS)
    @question_finder(controller)
    @controller.force_ack()
    def delete_question(self, event: DuplexEvent, question: Question) -> None:
        question.delete()
        event.emit_convert(
            room=self.room_name(question.test_id),
            test_id=question.test_id,
            question_id=question.id,
        )
