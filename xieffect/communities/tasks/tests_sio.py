from __future__ import annotations

from datetime import datetime
from typing import Any

from flask_fullstack import DuplexEvent, EventSpace
from flask_socketio import join_room, leave_room
from pydantic import BaseModel

from common import EventController, User
from communities.base.meta_db import Community, ParticipantRole
from communities.tasks.main_db import Task, TaskEmbed
from communities.tasks.tests_db import Test, Question, QuestionKind
from communities.utils import check_participant
from .main_sio import check_files

controller = EventController()


@controller.route()
class TasksEventSpace(EventSpace):
    @classmethod
    def room_name(cls, community_id: int) -> str:
        return f"cs-tasks-{community_id}"

    class CommunityIdModel(BaseModel):
        community_id: int

    class TestIdModel(BaseModel):
        test_id: int

    @controller.argument_parser(CommunityIdModel)
    @check_participant(controller, role=ParticipantRole.OWNER)
    @controller.force_ack()
    def open_tasks(self, community: Community):
        join_room(self.room_name(community.id))  # TODO pragma: no cover | task

    @controller.argument_parser(CommunityIdModel)
    @check_participant(controller, role=ParticipantRole.OWNER)
    @controller.force_ack()
    def close_tasks(self, community: Community):
        leave_room(self.room_name(community.id))  # TODO pragma: no cover | task

    class CreationModel(Test.CreateModel, CommunityIdModel):
        files: list[int] = []

    @controller.argument_parser(CreationModel)
    @controller.mark_duplex(Task.FullModel, use_event=True)
    @check_participant(controller, role=ParticipantRole.OWNER, use_user=True)
    @controller.marshal_ack(Task.FullModel)
    def new_test(
        self,
        event: DuplexEvent,
        community: Community,
        user: User,
        page_id: int,
        name: str,
        files: list[int],
        description: str | None,
        opened: datetime | None,
        closed: datetime | None,
    ):
        test: Test = Test.create(
            user.id, community.id, page_id, name, description, opened, closed
        )
        if len(files) != 0:
            TaskEmbed.add_files(test.id, check_files(files))
        event.emit_convert(test, self.room_name(community.id))
        return test

    class UpdateModel(CommunityIdModel, TestIdModel):
        page_id: int = None
        name: str = None
        files: list[int] = None
        description: str = None
        opened: datetime = None
        closed: datetime = None

        # Override dict method of BaseModel to set "exclude_none" argument on True
        def dict(self, *args, **kwargs) -> dict[str, Any]:  # noqa: A003
            kwargs["exclude_none"] = True
            return super().dict(*args, **kwargs)

    @controller.argument_parser(UpdateModel)
    @controller.mark_duplex(UpdateModel, use_event=True)
    @check_participant(controller, role=ParticipantRole.OWNER)
    @controller.database_searcher(Test)
    @controller.force_ack()
    def update_test(
        self,
        event: DuplexEvent,
        community: Community,
        test: Test,
        **kwargs,
    ):
        if test.community_id != community.id:
            controller.abort(404, Task.not_found_text)

        files: list[int] | None = kwargs.pop("files", None)
        if files is not None:
            new_files: set[int] = check_files(files)
            old_files: set[int] = set(TaskEmbed.get_task_files(test.id))
            TaskEmbed.delete_files(test.id, old_files - new_files)
            TaskEmbed.add_files(test.id, new_files - old_files)

        Test.update(test.id, **kwargs)
        event.emit_convert(
            room=self.room_name(community.id),
            community_id=community.id,
            test_id=test.id,
        )

    class DeleteModel(CommunityIdModel, TestIdModel):
        pass

    @controller.argument_parser(DeleteModel)
    @controller.mark_duplex(DeleteModel, use_event=True)
    @check_participant(controller, role=ParticipantRole.OWNER)
    @controller.database_searcher(Test)
    @controller.force_ack()
    def delete_test(self, event: DuplexEvent, community: Community, test: Test):
        if test.community_id != community.id:
            controller.abort(404, Test.not_found_text)
        test.soft_delete()
        event.emit_convert(
            room=self.room_name(community.id),
            community_id=community.id,
            test_id=test.id,
        )

    class QuestionCreationModel(Question.BaseModel, TestIdModel):
        pass

    @controller.argument_parser(QuestionCreationModel)
    @controller.mark_duplex(Question.BaseModel, use_event=True)
    @check_participant(controller, role=ParticipantRole.OWNER, use_user=True)
    @controller.database_searcher(Test)
    @controller.marshal_ack(Question.BaseModel)
    def new_question(
        self,
        event: DuplexEvent,
        community: Community,
        text: str,
        kind: QuestionKind,
        test: Test,
    ):
        question = Question.create(text, kind, test.id)
        event.emit_convert(question, self.room_name(community.id))
        return question

    class QuestionModel(BaseModel):
        question_id: int

    class QuestionUpdateModel(CommunityIdModel, QuestionModel):
        text: str
        kind: QuestionKind

        # Override dict method of BaseModel to set "exclude_none" argument on True
        def dict(self, *args, **kwargs) -> dict[str, Any]:  # noqa: A003
            kwargs["exclude_none"] = True
            return super().dict(*args, **kwargs)

    @controller.argument_parser(QuestionUpdateModel)
    @controller.mark_duplex(QuestionUpdateModel, use_event=True)
    @check_participant(controller, role=ParticipantRole.OWNER)
    @controller.database_searcher(Question)
    @controller.force_ack()
    def update_question(
        self, event: DuplexEvent, community: Community, question: Question, **kwargs
    ):
        Question.update(question.id, **kwargs)

        event.emit_convert(
            room=self.room_name(community.id),
            community_id=community.id,
            question_id=question.id,
        )

    class QuestionDeleteModel(CommunityIdModel, QuestionModel):
        pass

    @controller.argument_parser(QuestionDeleteModel)
    @controller.mark_duplex(QuestionDeleteModel, use_event=True)
    @check_participant(controller, role=ParticipantRole.OWNER)
    @controller.database_searcher(Question)
    @controller.force_ack()
    def delete_question(
        self, event: DuplexEvent, community: Community, question: Question
    ):
        question.soft_delete()
        event.emit_convert(
            room=self.room_name(community.id),
            community_id=community.id,
            question_id=question.id,
        )
