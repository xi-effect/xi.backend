from __future__ import annotations

from flask_fullstack import DuplexEvent, EventSpace
from flask_socketio import join_room, leave_room

from common import EventController
from communities.base.meta_db import PermissionType, Community
from communities.base.utils import check_permission
from communities.tasks.tests_db import Test, Question, QuestionKind
from communities.tasks.tests_sio import TestsEventSpace
from communities.tasks.utils import test_finder, question_finder

controller: EventController = EventController()


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
        question: Question = Question.create(text, kind, test.id)
        event.emit_convert(question, self.room_name(test.id))
        return question

    class QuestionIdModel(TestsEventSpace.TestIdModel):
        question_id: int

    class UpdateModel(QuestionIdModel, Question.UpdateModel):
        pass

    @controller.doc_abort(400, "Is not a valid QuestionKind")
    @controller.argument_parser(UpdateModel)
    @controller.mark_duplex(Question.FullModel, use_event=True)
    @check_permission(controller, PermissionType.MANAGE_TASKS)
    @question_finder(controller)
    @controller.marshal_ack(Question.FullModel)
    def update_question(
        self,
        event: DuplexEvent,
        question: Question,
        **kwargs,
    ) -> Question:
        question.update(**kwargs)
        event.emit_convert(question, room=self.room_name(question.id))
        return question

    @controller.argument_parser(QuestionIdModel)
    @controller.mark_duplex(QuestionIdModel, use_event=True)
    @check_permission(controller, PermissionType.MANAGE_TASKS)
    @question_finder(controller, use_community=True)
    @controller.force_ack()
    def delete_question(
        self, event: DuplexEvent, question: Question, community: Community
    ) -> None:
        question.delete()
        event.emit_convert(
            room=self.room_name(question.test_id),
            test_id=question.test_id,
            question_id=question.id,
            community_id=community.id,
        )
